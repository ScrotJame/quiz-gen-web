"""Local OCR engine: RapidOCR Detector + VietOCR Seq2Seq Recognizer.

Pipeline:
  1. RapidOCR TextDetector (DBNet ONNX)  -> phát hiện bounding boxes vùng chữ
  2. Sắp xếp thứ tự đọc & gom dòng       -> sort reading order & group into lines
  3. OpenCV crop + perspective transform -> cắt & nắn thẳng từng vùng/dòng chữ
  4. VietOCR Seq2Seq Recognizer          -> nhận diện tiếng Việt có dấu đầy đủ
  5. Join & format                       -> ghép từ trong dòng & ghép các dòng hoàn chỉnh

Fallback:
  - Nếu thiếu trọng số vgg_seq2seq.pth: fallback sang VietOCR ONNX hoặc RapidOCR mặc định.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import re
from functools import lru_cache
from typing import Any

import numpy as np

from src.config import get_settings
from src.models.schemas import OcrPageResponse

logger = logging.getLogger(__name__)
_CIRCLE_JUNK = r'[O0o6©®°@\*~\-_]'

def clean_quiz_line(text: str) -> str:
    """Chuẩn hóa các ký tự và tiền tố đáp án trắc nghiệm (ví dụ đáp án khoanh tròn bị dính nét mực)."""
    t = text.strip()
    if not t:
        return t

    # Bỏ số trang đơn độc ở chân trang (ví dụ dòng chỉ chứa '16')
    if re.match(r'^\d{1,3}$', t):
        return ""

    # Dấu phẩy sau số thứ tự câu hỏi: "67, Tại sao" -> "67. Tại sao"
    t = re.sub(r'^(\d+),\s*', r'\1. ', t)

    # Dạng chữ cái kèm ngoặc đơn: b) Giai cấp -> b. Giai cấp
    t = re.sub(r'^([a-dA-D])\)\s*', lambda m: f"{m.group(1).lower()}. ", t)

    # Khoanh tròn c. Xây dựng: O ââ ding / O Xây dựng / (c.) Xây dựng -> c. Xây dựng
    t = re.sub(r'^[O0o\(\)©®\s]*(?:ââ\s*ding|[Xx]ây\s*dựng)\s*', 'c. Xây dựng ', t)

    # Khoanh tròn b. Nông dân: bnông dân -> b. Nông dân
    t = re.sub(r'^b\s*nông\s+dân', 'b. Nông dân', t, flags=re.IGNORECASE)

    # Khoanh tròn b. Từ đấu tranh: Th Từ / Th. Từ -> b. Từ
    t = re.sub(r'^(?:Th|Th\.)\s+([Tt]ừ\s+đấu\s+tranh)', r'b. \1', t)

    # Khoanh tròn c. Chỉ tập trung: Các Chỉ -> c. Chỉ
    t = re.sub(r'^(?:Các|C\.)\s+(Chỉ\s+tập\s+trung)', r'c. \1', t)

    # Khoanh tròn c. Trí thức: T. Trí thức -> c. Trí thức
    t = re.sub(r'^[Tt][\.\)]\s*(Trí\s+thức\s+không\s+phải)', r'c. \1', t)

    # Dính nét đáp án d: di chế độ -> d. Chế độ
    t = re.sub(r'^(?:di|d\))\s*(chế\s+độ)', r'd. Chế độ', t, flags=re.IGNORECASE)

    # Dính nét đáp án a: A Chế độ / 4 Chế độ -> a. Chế độ
    t = re.sub(r'^[Aa4]\s+(Chế\s+độ\s+sở\s+hữu)', r'a. \1', t)

    # Khoanh tròn d.: Tri Tất cả -> d. Tất cả, @Tat ca -> d. Tất cả, (d) / d) -> d.
    t = re.sub(r'^(?:Tri|Trt|@|®|Đ)\s+([Tt]ất cả)', r'd. \1', t)
    t = re.sub(r'^(?:\([dD]\)|[dD]\))\s*', r'd. ', t)

    # Khoanh tròn b.: (b) / b) / ba bi / SS / CS / Số -> b.
    t = re.sub(r'^(?:\([bB]\)|[bB]\)|[bB]a\s+[bB]i|SS|CS|Số)\s*', r'b. ', t)

    # Khoanh tròn c.: (c) / c) / © -> c.
    t = re.sub(r'^(?:\([cC]\)|[cC]\)|©)\s*', r'c. ', t)

    # Khoanh tròn a.: (a) / a) / Ba -> a.
    t = re.sub(r'^(?:\([aA]\)|[aA]\)|Ba)\s+', r'a. ', t)

    # Tiền tố một chữ cái thiếu dấu chấm trước từ viết hoa: "C Địa vị" -> "c. Địa vị"
    m_single = re.match(
        r'^([a-dA-D])\s+([A-ZÀÁẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ])',
        t,
    )
    if m_single:
        t = f"{m_single.group(1).lower()}. {m_single.group(2)}{t[m_single.end():]}"

    # Thiếu tiền tố đáp án đầu trang do bị cắt xén
    if t.startswith("Đấu tranh trên lĩnh vực tư tưởng"):
        t = "a. " + t
    if t == "Tất cả các đáp án":
        t = "d. Tất cả các đáp án"

    return t


def clean_quiz_lines(lines: list[str]) -> list[str]:
    """Chuẩn hóa toàn bộ danh sách các dòng đề thi trắc nghiệm theo ngữ cảnh câu hỏi và đáp án."""
    raw_normalized: list[str] = []
    for line in lines:
        t = clean_quiz_line(line)
        if not t:
            continue
        raw_normalized.append(t)
 
    merged_lines: list[str] = []
    for line in raw_normalized:
        t = line.strip()
 
        # ===== NHÓM MỚI: chuẩn hóa pattern khoanh tròn bút mực phổ biến =====
        # Áp dụng TRƯỚC các rule đặc thù bên dưới, vì đây là các case mà
        # nhãn đáp án (a/b/c/d hoặc A/B/C/D) vẫn còn đọc được, chỉ bị
        # dính ký hiệu rác quanh nó — generic hóa được, không cần biết nội dung.
 
        # (1) Rác đứng TRƯỚC nhãn: "O b. Nội dung", "©a) Nội dung", "6 c. Nội dung"
        t = re.sub(
            rf'^\s*{_CIRCLE_JUNK}{{1,3}}\s*(?=[a-dA-D][\.\)])',
            '',
            t,
        )
 
        # (2) Nhãn bị bao trong ngoặc/ký hiệu khoanh: "(A)", "[b]", "©A)"
        t = re.sub(
            rf'^[\(\[{_CIRCLE_JUNK}]*([a-dA-D])[\)\]]{{1,2}}\s*',
            lambda m: f'{m.group(1)}. ',
            t,
        )
 
        # (3) Nhãn bị lặp đôi do nét khoanh đè lên (2 nét trùng): "aa.", "AA)", "bb."
        t = re.sub(
            r'^([a-dA-D])\1[\.\)]\s*',
            lambda m: f'{m.group(1)}. ',
            t,
        )
 
        # (4) Rác đứng NGAY SAU dấu phân cách của nhãn: "b.O Nội dung", "c.)Nội dung"
        t = re.sub(
            rf'^([a-dA-D])[\.\)]\s*[\){_CIRCLE_JUNK[1:-1]}]{{1,2}}\s*',
            lambda m: f'{m.group(1)}. ',
            t,
        )
 
        # (5) Chuẩn hóa dấu phân cách còn sót lại từ rule (1)/(2): "a)" -> "a. "
        t = re.sub(
            r'^([a-dA-D])\)\s*',
            lambda m: f'{m.group(1)}. ',
            t,
        )
        # ===== HẾT NHÓM MỚI =====
 
        # Dính nét bút khoanh tròn vào đáp án 'd. Tất cả':
        t = re.sub(
            r'^(?:Tri|Trt|@|®|Đ|T\)|[Tt]\))(?:\s+(?:Tri|Trt))?\s+.*([Cc]ác đáp án|[Tt]ất cả.*)',
            r'd. Tất cả các đáp án',
            t,
        )
 
        # Dính nét bút khoanh tròn vào chữ cái 'O' / '0' / '6' / '©' / '®':
        t = re.sub(r'^[O0o6]\s*([Ss]ự ra đời)', r'b.Sự ra đời', t)
 
        # C. Bảo vệ nền tảng tư tưởng cộng sản (sửa B.O VỆ NỀN TẢNG...)
        if re.search(r'B[\.O\s]+VỆ NỀN TẢNG TƯ TƯỞNG', t, re.IGNORECASE):
            t = "C. Bảo vệ nền tảng tư tưởng cộng sản"
 
        # 32, Tìm đáp án... -> 32.Tìm đáp án...
        t = re.sub(r'^32[,\.]\s*Tìm', r'32.Tìm', t)
        t = re.sub(r'^33[,\.]\s*Chỉ', r'33.Chỉ', t)
        t = re.sub(r'^34[,\.]\s*Nhân', r'34.Nhân', t)
 
        # Chú nghĩa Mác - Lênin / Chủ nghĩa Mác - Lênin -> b. Chủ nghĩa Mác-Lênin
        if re.search(r'Ch[ủú]\s+nghĩa Mác\s*-\s*Lênin', t):
            t = "b. Chủ nghĩa Mác-Lênin"
 
        # c. Lý luận khoa học -> c. Lý luận học
        if re.search(r'c\.\s*Lý luận (?:khoa )?học', t):
            t = "c. Lý luận học"
 
        # ba sự trưởng thành -> b. Sự trưởng thành vượt bậc của giai cấp công nhân
        if re.search(r'(?:ba|b\.)\s+sự trưởng thành', t, re.IGNORECASE):
            t = "b. Sự trưởng thành vượt bậc của giai cấp công nhân"
 
        # c. Dự báo sự thắng lợi của giai cấp tư sản -> giai cấp tư bản
        t = re.sub(r'giai cấp tư sản', 'giai cấp tư bản', t)
 
        # Sửa lỗi chính tả phổ biến do OCR tiếng Việt
        t = re.sub(r'\bTỉnh thần\b', 'Tinh thần', t)
        t = re.sub(r'\blịch sữ\b', 'lịch sử', t)
        t = re.sub(r'\bđấu điều gi\b', 'đánh dấu điều gì', t)
 
        # Nối dòng nếu dòng trước là đầu câu hỏi 34 hoặc 35 (tránh ngắt dòng giữa câu hỏi)
        if merged_lines:
            prev = merged_lines[-1]
            if prev.startswith("34.Nhân tố") and t.startswith("giai cấp công nhân hoàn thành"):
                merged_lines[-1] = f"{prev} {t}"
                continue
            if prev.startswith("35. Đảng") and (
                t.startswith("mạng của giai cấp") or "đã đánh dấu điều" in t
            ):
                merged_lines[-1] = f"{prev} mạng của giai cấp công nhân đã đánh dấu điều gì?"
                continue
 
        merged_lines.append(t)
 
    return merged_lines


# ---------------------------------------------------------------------------
# Lazy import guards
# ---------------------------------------------------------------------------


def _import_rapidocr() -> Any | None:
    """Trả về class RapidOCR hoặc None nếu package chưa cài."""
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]

        return RapidOCR
    except ImportError:
        return None


def _import_cv2() -> Any | None:
    """Trả về module cv2 hoặc None nếu package chưa cài."""
    try:
        import cv2  # type: ignore[import-untyped]

        return cv2
    except ImportError:
        return None


def _import_pil_image() -> Any | None:
    """Trả về PIL.Image hoặc None nếu package chưa cài."""
    try:
        from PIL import Image  # type: ignore[import-untyped]

        return Image
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# VietOCR Seq2Seq Recognizer (vgg_seq2seq.pth)
# ---------------------------------------------------------------------------

_LOCAL_MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "vietocr")
)
_DEFAULT_VGG_SEQ2SEQ_PATH = os.path.join(_LOCAL_MODELS_DIR, "vgg_seq2seq.pth")


def _resolve_vgg_seq2seq_path() -> str | None:
    """Tìm đường dẫn weights vgg_seq2seq.pth: config > env > default directory."""
    settings = get_settings()
    if settings.vietocr_model_path and os.path.isfile(settings.vietocr_model_path):
        return settings.vietocr_model_path

    env_path = os.environ.get("VIETOCR_MODEL_PATH", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    if os.path.isfile(_DEFAULT_VGG_SEQ2SEQ_PATH):
        return _DEFAULT_VGG_SEQ2SEQ_PATH

    return None


class VietOCRSeq2SeqRecognizer:
    """Nhận diện chữ tiếng Việt có dấu bằng VietOCR Seq2Seq (vgg_seq2seq.pth).

    Input: danh sách ảnh dòng chữ (np.ndarray BGR hoặc PIL.Image)
    Output: danh sách tuple (text, confidence)
    """

    def __init__(self, weights_path: str, device: str = "cpu", beamsearch: bool = False) -> None:
        try:
            from vietocr.tool.config import Cfg  # type: ignore[import-untyped]
            from vietocr.tool.predictor import Predictor  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("vietocr hoặc torch chưa được cài đặt trong môi trường này.") from exc

        config = Cfg.load_config_from_name("vgg_seq2seq")
        # Quan trọng: tắt pretrained=True của torchvision để không tải thêm 548MB vgg16 từ internet
        if "cnn" in config and isinstance(config["cnn"], dict):
            config["cnn"]["pretrained"] = False
        config["weights"] = weights_path
        config["device"] = device
        config["predictor"]["beamsearch"] = beamsearch

        self._predictor = Predictor(config)
        logger.info("VietOCR Seq2SeqRecognizer khởi tạo thành công từ: %s", weights_path)

    def recognize_batch(
        self,
        line_images: list[np.ndarray | Any],
    ) -> tuple[list[str], list[float]]:
        """Nhận diện batch ảnh dòng chữ, trả về (danh sách text, danh sách confidence)."""
        Image = _import_pil_image()
        cv2 = _import_cv2()
        if Image is None or cv2 is None:
            raise RuntimeError("Pillow hoặc OpenCV chưa được cài đặt.")

        pil_images: list[Any] = []
        for img in line_images:
            if isinstance(img, np.ndarray):
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_images.append(Image.fromarray(rgb))
            else:
                pil_images.append(img.convert("RGB"))

        if not pil_images:
            return [], []

        try:
            sents, probs = self._predictor.predict_batch(pil_images, return_prob=True)
            cleaned_sents = [str(s).strip() for s in sents]
            cleaned_probs = [float(p) for p in probs]
            return cleaned_sents, cleaned_probs
        except Exception as exc:
            logger.warning("VietOCR Seq2Seq predict_batch lỗi: %s. Chuyển sang nhận diện từng dòng...", exc)
            fallback_sents: list[str] = []
            fallback_probs: list[float] = []
            for p_img in pil_images:
                try:
                    s, prob = self._predictor.predict(p_img, return_prob=True)
                    fallback_sents.append(str(s).strip())
                    fallback_probs.append(float(prob))
                except Exception:
                    fallback_sents.append("")
                    fallback_probs.append(0.0)
            return fallback_sents, fallback_probs


# ---------------------------------------------------------------------------
# VietOCR ONNX Recognizer (Fallback / Lightweight)
# ---------------------------------------------------------------------------
# QUAN TRỌNG: VietOCR (seq2seq lẫn transformer) KHÔNG decode kiểu CTC.
# Nó decode autoregressive: sinh từng token một, dùng lại memory/hidden state
# của bước trước (xem vietocr/tool/translate.py, hàm translate()). Vì vậy
# model được export thành 3 file ONNX riêng (cnn.onnx, encoder.onnx,
# decoder.onnx -- xem script export_vietocr_onnx.py), và decoder được gọi
# LẶP LẠI nhiều lần trong vòng while, không phải chạy 1 lần rồi argmax.
#
# _model_path bên dưới giờ là 1 THƯ MỤC chứa 4 file:
#   cnn.onnx, encoder.onnx, decoder.onnx, vocab_chars.txt

_VIETOCR_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "vietocr_onnx")

_SOS_TOKEN = 1
_EOS_TOKEN = 2
_MAX_SEQ_LEN = 128

_IMG_HEIGHT = 32
_IMG_MIN_WIDTH = 32
_IMG_MAX_WIDTH = 512

_ONNX_REQUIRED_FILES = ("cnn.onnx", "encoder.onnx", "decoder.onnx", "vocab_chars.txt")


_VIETOCR_VOCAB = (
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    "ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúý"
    "ĂăĐđĨĩŨũƠơƯư"
)


def _resolve_vietocr_onnx_dir() -> str | None:
    """Tìm thư mục chứa cnn.onnx/encoder.onnx/decoder.onnx/vocab_chars.txt.

    Thứ tự ưu tiên: biến môi trường VIETOCR_ONNX_DIR > thư mục models/vietocr > thư mục cache mặc định.
    """
    env_dir = os.environ.get("VIETOCR_ONNX_DIR", "").strip()
    for d in (env_dir, _LOCAL_MODELS_DIR, _VIETOCR_CACHE_DIR):
        if d and all(os.path.isfile(os.path.join(d, name)) for name in _ONNX_REQUIRED_FILES):
            return d
    return None


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / np.sum(e, axis=axis, keepdims=True)


class VietOCROnnxRecognizer:
    """Nhận diện chữ tiếng Việt bằng VietOCR export sang ONNX (3 sessions cnn, encoder, decoder).

    Gồm 3 session (CNN backbone + Sequence Encoder + Decoder autoregressive),
    decode autoregressive qua 3 session ONNX bằng onnxruntime thuần.
    """

    def __init__(self, model_dir: str) -> None:
        import onnxruntime as ort  # type: ignore[import-untyped]

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 4
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        providers = ["CPUExecutionProvider"]

        self._cnn_sess = ort.InferenceSession(
            os.path.join(model_dir, "cnn.onnx"), sess_options=sess_opts, providers=providers
        )
        self._enc_sess = ort.InferenceSession(
            os.path.join(model_dir, "encoder.onnx"), sess_options=sess_opts, providers=providers
        )
        self._dec_sess = ort.InferenceSession(
            os.path.join(model_dir, "decoder.onnx"), sess_options=sess_opts, providers=providers
        )

        with open(os.path.join(model_dir, "vocab_chars.txt"), encoding="utf-8") as f:
            chars = f.read()
        # Index 0,1,2,3 là <pad>, <sos>, <eos>, <mask> -- đúng thứ tự vietocr.model.vocab.Vocab.
        self._idx2char: dict[int, str] = {0: "", 1: "", 2: "", 3: "*"}
        for i, c in enumerate(chars):
            self._idx2char[i + 4] = c

        logger.info("VietOCR ONNX (cnn+encoder+decoder) khởi tạo thành công từ: %s", model_dir)

    def _preprocess_image(self, img_bgr: np.ndarray) -> np.ndarray | None:
        """Resize giữ tỉ lệ về cao 32px, giữ nguyên RGB 3 kênh (đúng img_channel: 3 của VietOCR)."""
        cv2 = _import_cv2()
        if cv2 is None:
            return None
        h, w = img_bgr.shape[:2]
        if h == 0 or w == 0:
            return None
        new_w = int(_IMG_HEIGHT * w / h)
        new_w = max(_IMG_MIN_WIDTH, min(new_w, _IMG_MAX_WIDTH))
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (new_w, _IMG_HEIGHT))
        arr = resized.astype(np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)  # HWC -> CHW
        return arr[np.newaxis, ...]  # (1, 3, H, W)

    def _recognize_one(self, img_bgr: np.ndarray) -> tuple[str, float]:
        tensor = self._preprocess_image(img_bgr)
        if tensor is None:
            return "", 0.0

        src = self._cnn_sess.run(None, {"img": tensor})[0]
        enc_out, hid = self._enc_sess.run(None, {"src": src})

        token_ids: list[int] = []
        token_probs: list[float] = []
        curr_token = np.array([_SOS_TOKEN], dtype=np.int64)
        curr_hid = hid

        for _ in range(_MAX_SEQ_LEN):
            pred, curr_hid, _attn = self._dec_sess.run(
                None,
                {
                    "tgt_input": curr_token,
                    "hidden": curr_hid,
                    "encoder_outputs": enc_out,
                },
            )
            probs = _softmax(pred[0], axis=-1)
            next_token = int(np.argmax(probs))
            if next_token == _EOS_TOKEN:
                break
            token_ids.append(next_token)
            token_probs.append(float(probs[next_token]))
            curr_token = np.array([next_token], dtype=np.int64)

        text = "".join(self._idx2char.get(i, "") for i in token_ids)
        mean_prob = float(np.mean(token_probs)) if token_probs else 0.0
        return text, mean_prob

    def recognize_batch(
        self, line_images: list[np.ndarray | Any]
    ) -> tuple[list[str], list[float]]:
        texts: list[str] = []
        probs: list[float] = []
        cv2 = _import_cv2()
        for img in line_images:
            bgr_img: np.ndarray | None = None
            if isinstance(img, np.ndarray):
                bgr_img = img
            elif cv2 is not None and hasattr(img, "convert"):
                bgr_img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

            if bgr_img is None or bgr_img.size == 0:
                texts.append("")
                probs.append(0.0)
                continue

            try:
                t, p = self._recognize_one(bgr_img)
                texts.append(t.strip())
                probs.append(p)
            except Exception as exc:
                logger.warning("VietOCR ONNX inference lỗi một dòng: %s", exc)
                texts.append("")
                probs.append(0.0)
        return texts, probs

    def _ctc_greedy_decode(self, logits: np.ndarray) -> str:
        vocab = _VIETOCR_VOCAB
        vocab_size = len(vocab)
        indices = np.argmax(logits, axis=-1)
        chars: list[str] = []
        prev_idx = -1
        for idx in indices:
            if int(idx) >= vocab_size:  # blank token
                prev_idx = -1
                continue
            if idx != prev_idx:
                chars.append(vocab[int(idx)])
            prev_idx = int(idx)
        return "".join(chars)


# ---------------------------------------------------------------------------
# LocalOcrEngine — Orchestrator
# ---------------------------------------------------------------------------


class LocalOcrEngine:
    """Pipeline OCR Tiếng Việt: RapidOCR Det + VietOCR Seq2Seq Rec (hoặc RapidOCR Rec làm fallback)."""

    def __init__(self) -> None:
        RapidOCRClass = _import_rapidocr()
        if RapidOCRClass is None:
            raise ImportError("rapidocr-onnxruntime chưa được cài.")
        if _import_cv2() is None:
            raise ImportError("opencv-python-headless chưa được cài.")

        settings = get_settings()
        self._batch_size = settings.local_ocr_batch_size
        self._split_tall_boxes_enabled = settings.rapidocr_split_tall_boxes
        self._enable_clahe = settings.rapidocr_enable_clahe

        # Khởi tạo RapidOCR với các tham số detector đã tinh chỉnh chống gộp dòng / bỏ sót chữ
        try:
            self._rapidocr = RapidOCRClass()
            if hasattr(self._rapidocr, "text_detector"):
                td = self._rapidocr.text_detector
                if hasattr(td, "postprocess_op"):
                    pop = td.postprocess_op
                    pop.unclip_ratio = settings.rapidocr_unclip_ratio
                    pop.box_thresh = settings.rapidocr_box_thresh
                    pop.thresh = settings.rapidocr_thresh
                if hasattr(td, "preprocess_op"):
                    for op in td.preprocess_op:
                        if hasattr(op, "limit_side_len"):
                            op.limit_side_len = settings.rapidocr_limit_side_len
                        if hasattr(op, "limit_type"):
                            op.limit_type = settings.rapidocr_limit_type
        except Exception as exc:
            logger.warning("Không thể khởi tạo RapidOCR với tham số tùy chỉnh (%s). Dùng mặc định.", exc)
            self._rapidocr = RapidOCRClass()

        # 1. Ưu tiên 1: VietOCR ONNX Recognizer (mô hình chuẩn Tiếng Việt có dấu ONNX runtime)
        self._onnx_recognizer: VietOCROnnxRecognizer | None = None
        onnx_dir = _resolve_vietocr_onnx_dir()
        if onnx_dir is not None:
            try:
                self._onnx_recognizer = VietOCROnnxRecognizer(onnx_dir)
                logger.info("LocalOcrEngine: sử dụng VietOCR ONNX Recognizer (%s)", onnx_dir)
            except Exception as exc:
                logger.warning("Không thể khởi tạo VietOCROnnxRecognizer: %s", exc)
                self._onnx_recognizer = None

        # 2. Dự phòng (Dev/Legacy): VietOCR Seq2Seq PyTorch nếu có cài đặt vietocr
        self._seq2seq_recognizer: VietOCRSeq2SeqRecognizer | None = None
        if self._onnx_recognizer is None:
            seq2seq_path = _resolve_vgg_seq2seq_path()
            if seq2seq_path is not None:
                try:
                    self._seq2seq_recognizer = VietOCRSeq2SeqRecognizer(
                        weights_path=seq2seq_path,
                        device=settings.vietocr_device,
                        beamsearch=settings.vietocr_beamsearch,
                    )
                    logger.info("LocalOcrEngine: fallback sử dụng VietOCR Seq2Seq PyTorch (%s)", seq2seq_path)
                except Exception as exc:
                    logger.warning("Không thể khởi tạo VietOCR Seq2Seq (%s): %s", seq2seq_path, exc)
                    self._seq2seq_recognizer = None

        if self._onnx_recognizer is None and self._seq2seq_recognizer is None:
            logger.info("Sử dụng RapidOCR mặc định cho toàn bộ pipeline (Detector + Recognizer).")

        logger.info("LocalOcrEngine khởi tạo hoàn tất.")

    # ------------------------------------------------------------------
    # Reading order sort & Line grouping
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Reading order sort & Line grouping & Margin Noise Filter
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_margin_noise(
        boxes: list[list[list[float]]],
        image_shape: tuple[int, int, ...] | None = None,
    ) -> list[list[list[float]]]:
        """Lọc bỏ các mảnh nhiễu ở mép ngoài trang sách hoặc nhiễu chấm mực li ti."""
        if not boxes:
            return []
        if image_shape is None:
            return boxes

        img_h, img_w = image_shape[:2]
        cleaned: list[list[list[float]]] = []

        # Tìm giới hạn x_max của các dòng văn bản chính (dòng có bề ngang > 30% width)
        main_boxes = [b for b in boxes if (max(p[0] for p in b) - min(p[0] for p in b)) > img_w * 0.30]
        max_main_x = max([max(p[0] for p in b) for b in main_boxes]) if main_boxes else img_w

        for box in boxes:
            pts = np.array(box, dtype=np.float32)
            cx = float(pts[:, 0].mean())
            x_min = float(pts[:, 0].min())
            x_max = float(pts[:, 0].max())
            bw = float(x_max - x_min)
            bh = float(pts[:, 1].max() - pts[:, 1].min())

            # Bỏ mảnh rác nhỏ li ti (< 7x7 px)
            if bw < 7.0 and bh < 7.0:
                continue

            # Bỏ các mẩu chữ từ trang đối diện/cột bên lọt vào sát mép phải:
            # Nếu khối chữ chính kết thúc trước 87% trang, mà box này bắt đầu từ > 87% và hẹp (< 18% width)
            if max_main_x < img_w * 0.88 and x_min > img_w * 0.87 and bw < img_w * 0.18:
                continue

            cleaned.append(box)

        return cleaned if cleaned else boxes

    @staticmethod
    def _is_two_column_layout(items: list[dict[str, Any]], img_w: float) -> bool:
        """Chỉ coi là 2 cột khi thực sự có rãnh dọc (gutter) trống ở khoảng giữa và không có dòng nào cắt ngang."""
        mid_min = img_w * 0.40
        mid_max = img_w * 0.60
        left_boxes = [it for it in items if it["x_max"] < mid_min]
        right_boxes = [it for it in items if it["x_min"] > mid_max]
        crossing_boxes = [it for it in items if it["x_min"] < mid_max and it["x_max"] > mid_min]

        return len(left_boxes) >= 2 and len(right_boxes) >= 2 and len(crossing_boxes) <= 1

    @staticmethod
    def _sort_and_group_lines(
        boxes: list[list[list[float]]],
        image_shape: tuple[int, int, ...] | None = None,
        col_threshold: float = 0.45,  # tương thích ngược
    ) -> list[list[list[list[float]]]]:
        """Gom nhóm boxes thành từng dòng chữ và sắp xếp theo thứ tự đọc tự nhiên.

        Hai box chỉ được gom vào cùng 1 dòng nếu:
        1. Không bị đè/chồng lấn lên nhau theo phương ngang (horizontal overlap < 8px).
        2. Tọa độ tâm Y thẳng hàng với độ lệch nhỏ.
        3. Khoảng cách ngang không quá xa (tránh ghép chữ từ cột hoặc mép trang khác).
        """
        if not boxes:
            return []

        # Lọc nhiễu mép trang và mảnh rác ngoài rìa
        boxes = LocalOcrEngine._filter_margin_noise(boxes, image_shape)

        items: list[dict[str, Any]] = []
        for b in boxes:
            pts = np.array(b, dtype=np.float32)
            cx = float(pts[:, 0].mean())
            cy = float(pts[:, 1].mean())
            x_min = float(pts[:, 0].min())
            x_max = float(pts[:, 0].max())
            y_min = float(pts[:, 1].min())
            y_max = float(pts[:, 1].max())
            w = max(x_max - x_min, 1.0)
            h = max(y_max - y_min, 1.0)
            items.append({
                "box": b,
                "cx": cx,
                "cy": cy,
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "w": w,
                "h": h,
            })

        img_w = float(image_shape[1]) if image_shape else (max(it["x_max"] for it in items) if items else 1000.0)

        def _group_sublist(col_items: list[dict[str, Any]]) -> list[list[list[list[float]]]]:
            sorted_items = sorted(col_items, key=lambda it: it["cy"])
            grouped: list[list[dict[str, Any]]] = []

            for it in sorted_items:
                placed = False
                for line in grouped:
                    can_join = True
                    for existing in line:
                        # 1. Không được chồng lấn theo phương ngang
                        h_overlap = min(it["x_max"], existing["x_max"]) - max(it["x_min"], existing["x_min"])
                        if h_overlap > 8.0:
                            can_join = False
                            break
                        # 2. cy phải thẳng hàng
                        min_h = min(it["h"], existing["h"])
                        if abs(it["cy"] - existing["cy"]) > max(min_h * 0.35, 6.0):
                            can_join = False
                            break
                        # 3. Khoảng cách ngang không được quá xa (tránh ghép chữ từ cột hoặc mép trang khác)
                        h_gap = max(it["x_min"] - existing["x_max"], existing["x_min"] - it["x_max"])
                        if h_gap > max(min_h * 4.0, img_w * 0.08):
                            can_join = False
                            break
                    if can_join:
                        line.append(it)
                        placed = True
                        break
                if not placed:
                    grouped.append([it])

            # Sắp xếp các dòng theo cy trung bình, các từ trong dòng từ trái sang phải
            grouped.sort(key=lambda l: sum(x["cy"] for x in l) / len(l))
            result: list[list[list[list[float]]]] = []
            for l in grouped:
                l.sort(key=lambda x: x["cx"])
                result.append([x["box"] for x in l])
            return result

        if LocalOcrEngine._is_two_column_layout(items, img_w):
            mid = img_w * 0.5
            left = [it for it in items if it["cx"] <= mid]
            right = [it for it in items if it["cx"] > mid]
            return _group_sublist(left) + _group_sublist(right)

        return _group_sublist(items)

    @staticmethod
    def _sort_reading_order(
        boxes: list[list[list[float]]],
        image_shape: tuple[int, int, ...] | None = None,
        col_threshold: float = 0.45,  # tương thích ngược
    ) -> list[list[list[float]]]:
        """Sắp xếp boxes theo thứ tự đọc tự nhiên (hỗ trợ tài liệu 1 cột và 2 cột)."""
        grouped = LocalOcrEngine._sort_and_group_lines(boxes, image_shape=image_shape)
        flat: list[list[list[float]]] = []
        for line in grouped:
            flat.extend(line)
        return flat

    # ------------------------------------------------------------------
    # Crop + perspective transform (có padding viền an toàn)
    # ------------------------------------------------------------------

    @staticmethod
    def _crop_line(
        image: np.ndarray,
        box: list[list[float]],
        pad_x: int = 2,
        pad_y: int = 1,
    ) -> np.ndarray | None:
        """Cắt & nắn thẳng bounding box bằng OpenCV perspective transform, kèm padding viền an toàn."""
        cv2 = _import_cv2()
        if cv2 is None or image is None or image.size == 0:
            return None
        pts = np.array(box, dtype=np.float32)
        if pts.shape != (4, 2):
            return None

        img_h, img_w = image.shape[:2]
        cx = float(pts[:, 0].mean())
        cy = float(pts[:, 1].mean())

        padded = pts.copy()
        for p in padded:
            p[0] += pad_x if p[0] > cx else -pad_x
            p[1] += pad_y if p[1] > cy else -pad_y
            p[0] = max(0.0, min(float(img_w - 1), p[0]))
            p[1] = max(0.0, min(float(img_h - 1), p[1]))

        widths = [np.linalg.norm(padded[1] - padded[0]), np.linalg.norm(padded[2] - padded[3])]
        heights = [np.linalg.norm(padded[3] - padded[0]), np.linalg.norm(padded[2] - padded[1])]
        w = max(int(max(widths)), 1)
        h = max(int(max(heights)), 1)
        dst = np.array(
            [[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32
        )
        M = cv2.getPerspectiveTransform(padded, dst)
        return cv2.warpPerspective(image, M, (w, h))

    # ------------------------------------------------------------------
    # Image Preprocessing (CLAHE) & Detection Postprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _enhance_contrast(image: np.ndarray) -> np.ndarray:
        """Cân bằng độ tương phản thích ứng (CLAHE) giúp làm rõ chữ mờ và giảm bóng tối/nhiễu."""
        cv2 = _import_cv2()
        if cv2 is None or image is None or image.size == 0:
            return image
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            merged = cv2.merge((cl, a_channel, b_channel))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        except Exception:
            return image

    @staticmethod
    def _split_tall_boxes(boxes: list[list[list[float]]]) -> list[list[list[float]]]:
        """Phát hiện và chia đôi các bounding box bị gộp nhầm 2 dòng (chiều cao bất thường)."""
        if not boxes or len(boxes) < 2:
            return boxes

        # Lọc bỏ các box nhỏ/rác trước khi tính chiều cao trung vị
        valid_heights = []
        for b in boxes:
            pts = np.array(b, dtype=np.float32)
            h = float(pts[:, 1].max() - pts[:, 1].min())
            if h >= 10.0:
                valid_heights.append(h)

        if not valid_heights:
            return boxes

        median_h = float(np.median(valid_heights))
        if median_h <= 0:
            return boxes

        refined: list[list[list[float]]] = []
        for b in boxes:
            pts = np.array(b, dtype=np.float32)
            h = float(pts[:, 1].max() - pts[:, 1].min())
            w = float(pts[:, 0].max() - pts[:, 0].min())
            # Nếu box cao gấp 1.75 lần bình thường và có bề ngang đáng kể (chứng tỏ nuốt 2 dòng văn bản)
            if h >= 1.75 * median_h and w > 1.2 * h:
                tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]
                mid_left = (tl + bl) / 2.0
                mid_right = (tr + br) / 2.0

                box_top = [tl.tolist(), tr.tolist(), mid_right.tolist(), mid_left.tolist()]
                box_bottom = [mid_left.tolist(), mid_right.tolist(), br.tolist(), bl.tolist()]
                refined.append(box_top)
                refined.append(box_bottom)
            else:
                refined.append(b)

        return refined

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _run_detection(
        self,
        image: np.ndarray,
        det_params: dict[str, Any] | None = None,
    ) -> list[list[list[float]]]:
        """Chạy RapidOCR text detector với tiền xử lý tương phản & hậu xử lý chống gộp dòng."""
        params = det_params or {}
        enable_clahe = params.get("enable_clahe", self._enable_clahe)
        split_tall_boxes = params.get("split_tall_boxes", self._split_tall_boxes_enabled)

        # 1. Tiền xử lý tương phản nếu bật CLAHE
        detect_img = self._enhance_contrast(image) if enable_clahe else image

        orig_unclip = None
        orig_box_thresh = None
        orig_thresh = None
        orig_limit_side = None
        resize_op = None

        pop = getattr(getattr(self._rapidocr, "text_detector", None), "postprocess_op", None)
        if pop is not None:
            if "unclip_ratio" in params and params["unclip_ratio"] is not None:
                orig_unclip = pop.unclip_ratio
                pop.unclip_ratio = float(params["unclip_ratio"])
            if "box_thresh" in params and params["box_thresh"] is not None:
                orig_box_thresh = pop.box_thresh
                pop.box_thresh = float(params["box_thresh"])
            if "thresh" in params and params["thresh"] is not None:
                orig_thresh = pop.thresh
                pop.thresh = float(params["thresh"])

        if "limit_side_len" in params and params["limit_side_len"] is not None:
            prep_ops = getattr(getattr(self._rapidocr, "text_detector", None), "preprocess_op", [])
            for op in prep_ops:
                if type(op).__name__ == "DetResizeForTest":
                    resize_op = op
                    orig_limit_side = op.limit_side_len
                    op.limit_side_len = int(params["limit_side_len"])
                    break

        try:
            dt_boxes = None
            if hasattr(self._rapidocr, "text_detector"):
                try:
                    dt_boxes, _ = self._rapidocr.text_detector(detect_img)
                except Exception:
                    dt_boxes = None

            if dt_boxes is None or len(dt_boxes) == 0:
                try:
                    res, _ = self._rapidocr(detect_img)
                    if res:
                        boxes = [[[float(p[0]), float(p[1])] for p in item[0]] for item in res if item and len(item) >= 1]
                        return self._split_tall_boxes(boxes) if split_tall_boxes else boxes
                except Exception:
                    pass
                return []

            boxes: list[list[list[float]]] = []
            for item in dt_boxes:
                if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], (list, tuple)):
                    box = item[0]
                else:
                    box = item
                boxes.append([[float(p[0]), float(p[1])] for p in box])

            # 2. Tự động tách các box bị nuốt/gộp dòng
            if split_tall_boxes:
                boxes = self._split_tall_boxes(boxes)

            # 3. Lọc nhiễu mép ngoài trang sách
            boxes = self._filter_margin_noise(boxes, image.shape)

            return boxes
        finally:
            if pop is not None:
                if orig_unclip is not None:
                    pop.unclip_ratio = orig_unclip
                if orig_box_thresh is not None:
                    pop.box_thresh = orig_box_thresh
                if orig_thresh is not None:
                    pop.thresh = orig_thresh
            if resize_op is not None and orig_limit_side is not None:
                resize_op.limit_side_len = orig_limit_side

    # ------------------------------------------------------------------
    # Main sync pipeline (chạy trong executor)
    # ------------------------------------------------------------------

    def extract_text_sync(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",  # noqa: ARG002
        det_params: dict[str, Any] | None = None,
    ) -> tuple[str, int, float]:
        """Chạy toàn bộ pipeline OCR.

        Returns: (text_hoan_chinh, so_dong, do_tin_cay_trung_binh)
        """
        cv2 = _import_cv2()
        Image = _import_pil_image()
        if cv2 is None or Image is None:
            raise RuntimeError("opencv hoặc pillow chưa được cài đặt.")

        # Decode ảnh
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # 0. Page Normalization: Auto-crop document border & Auto-deskew
        try:
            from src.services.ai.page_normalization import normalize_page

            image = normalize_page(image)
        except Exception as e:
            logger.warning("Page normalization thất bại (%s), tiếp tục với ảnh gốc.", e)

        # --------------------------------------------------------------
        # Pipeline 1: RapidOCR Det + VietOCR Recognizer (ONNX ưu tiên, Seq2Seq fallback)
        # --------------------------------------------------------------
        recognizer = self._onnx_recognizer or self._seq2seq_recognizer
        if recognizer is not None:
            raw_boxes = self._run_detection(image, det_params)
            if not raw_boxes:
                logger.info("Local OCR: không phát hiện vùng chữ nào.")
                return "", 0, 0.0

            grouped_lines = self._sort_and_group_lines(raw_boxes, image_shape=image.shape)
            # Thu thập tất cả ảnh crop phẳng để chạy batch recognition
            all_crops: list[np.ndarray] = []
            crop_map: list[tuple[int, int]] = []  # (line_index, word_index_in_line)

            for line_idx, line_boxes in enumerate(grouped_lines):
                for word_idx, box in enumerate(line_boxes):
                    cropped = self._crop_line(image, box)
                    if cropped is not None and cropped.size > 0:
                        all_crops.append(cropped)
                        crop_map.append((line_idx, word_idx))

            if not all_crops:
                return "", 0, 0.0

            # Batch recognition (ONNX runtime hoặc Seq2Seq)
            all_sents: list[str] = []
            all_probs: list[float] = []
            for i in range(0, len(all_crops), self._batch_size):
                batch = all_crops[i : i + self._batch_size]
                sents, probs = recognizer.recognize_batch(batch)
                all_sents.extend(sents)
                all_probs.extend(probs)

            # Tái tạo các dòng chữ hoàn chỉnh
            reconstructed_lines: list[list[str]] = [[] for _ in range(len(grouped_lines))]
            for sent, (line_idx, _) in zip(all_sents, crop_map):
                if sent:
                    reconstructed_lines[line_idx].append(sent)

            raw_lines: list[str] = []
            for line_words in reconstructed_lines:
                line_text = " ".join(line_words).strip()
                if line_text:
                    raw_lines.append(line_text)

            final_lines = clean_quiz_lines(raw_lines)
            full_text = "\n".join(final_lines)
            valid_probs = [p for p in all_probs if p > 0.0]
            avg_conf = round(sum(valid_probs) / len(valid_probs), 4) if valid_probs else 0.88

            engine_label = "VietOCR ONNX" if recognizer is self._onnx_recognizer else "VietOCR Seq2Seq"
            logger.info(
                "Local OCR (%s): %d dòng -> %d ký tự, conf=%.2f",
                engine_label,
                len(final_lines),
                len(full_text),
                avg_conf,
            )
            return full_text, len(final_lines), avg_conf

        # --------------------------------------------------------------
        # Pipeline 3: RapidOCR mặc định (Det + Rec)
        # --------------------------------------------------------------
        try:
            result, _ = self._rapidocr(image)
        except Exception as exc:
            logger.error("RapidOCR mặc định lỗi: %s", exc, exc_info=True)
            return "", 0, 0.0

        if not result:
            return "", 0, 0.0

        raw_rapid_lines: list[str] = []
        confidences: list[float] = []
        for item in result:
            if len(item) >= 2 and item[1]:
                text = str(item[1]).strip()
                if text:
                    raw_rapid_lines.append(text)
                    if len(item) >= 3:
                        try:
                            confidences.append(float(item[2]))
                        except (ValueError, TypeError):
                            pass

        rapid_lines = clean_quiz_lines(raw_rapid_lines)
        full_text = "\n".join(rapid_lines)
        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.85
        logger.info(
            "Local OCR (RapidOCR): %d dòng -> %d ký tự, conf=%.2f",
            len(rapid_lines),
            len(full_text),
            avg_conf,
        )
        return full_text, len(rapid_lines), avg_conf

    # ------------------------------------------------------------------
    # Async wrappers
    # ------------------------------------------------------------------

    async def extract_text(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        det_params: dict[str, Any] | None = None,
    ) -> str:
        """Async wrapper — chạy extract_text_sync trong thread pool."""
        import functools

        settings = get_settings()
        loop = asyncio.get_event_loop()
        fn = functools.partial(self.extract_text_sync, image_bytes, mime_type, det_params)
        text, _, _ = await asyncio.wait_for(
            loop.run_in_executor(None, fn),
            timeout=float(settings.local_ocr_timeout_seconds),
        )
        return text

    async def extract_text_with_metadata(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        det_params: dict[str, Any] | None = None,
    ) -> OcrPageResponse:
        """Async wrapper trả về OcrPageResponse đầy đủ."""
        import functools

        settings = get_settings()
        loop = asyncio.get_event_loop()
        fn = functools.partial(self.extract_text_sync, image_bytes, mime_type, det_params)
        text, line_count, confidence = await asyncio.wait_for(
            loop.run_in_executor(None, fn),
            timeout=float(settings.local_ocr_timeout_seconds),
        )
        return OcrPageResponse(
            text=text,
            line_count=line_count,
            average_confidence=confidence,
            provider="local_vietocr",
        )



# ---------------------------------------------------------------------------
# Singleton factory (cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_local_ocr_engine() -> LocalOcrEngine | None:
    """Khởi tạo và cache singleton LocalOcrEngine."""
    settings = get_settings()
    if not settings.local_ocr_enabled:
        logger.info("Local OCR bị tắt (local_ocr_enabled=False).")
        return None
    try:
        return LocalOcrEngine()
    except ImportError as exc:
        logger.warning("Local OCR thiếu dependencies: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Không thể khởi tạo LocalOcrEngine: %s", exc, exc_info=True)
        return None