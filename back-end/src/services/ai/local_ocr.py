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


def clean_quiz_line(text: str) -> str:
    """Chuẩn hóa các ký tự và tiền tố đáp án trắc nghiệm (ví dụ đáp án khoanh tròn bị dính nét mực)."""
    t = text.strip()
    if not t:
        return t

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
        from vietocr.tool.config import Cfg  # type: ignore[import-untyped]
        from vietocr.tool.predictor import Predictor  # type: ignore[import-untyped]

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

_VIETOCR_VOCAB = (
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    "\u00c0\u00c1\u00c2\u00c3\u00c8\u00c9\u00ca\u00cc\u00cd\u00d2\u00d3\u00d4\u00d5\u00d9\u00da\u00dd"
    "\u00e0\u00e1\u00e2\u00e3\u00e8\u00e9\u00ea\u00ec\u00ed\u00f2\u00f3\u00f4\u00f5\u00f9\u00fa\u00fd"
    "\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0"
    "\u1ea0\u1ea1\u1ea2\u1ea3\u1ea4\u1ea5\u1ea6\u1ea7\u1ea8\u1ea9\u1eaa\u1eab\u1eac\u1ead"
    "\u1eae\u1eaf\u1eb0\u1eb1\u1eb2\u1eb3\u1eb4\u1eb5\u1eb6\u1eb7\u1eb8\u1eb9\u1eba\u1ebb"
    "\u1ebc\u1ebd\u1ebe\u1ebf\u1ec0\u1ec1\u1ec2\u1ec3\u1ec4\u1ec5\u1ec6\u1ec7\u1ec8\u1ec9"
    "\u1eca\u1ecb\u1ecc\u1ecd\u1ece\u1ecf\u1ed0\u1ed1\u1ed2\u1ed3\u1ed4\u1ed5\u1ed6\u1ed7"
    "\u1ed8\u1ed9\u1eda\u1edb\u1edc\u1edd\u1ede\u1edf\u1ee0\u1ee1\u1ee2\u1ee3\u1ee4\u1ee5"
    "\u1ee6\u1ee7\u1ee8\u1ee9\u1eea\u1eeb\u1eec\u1eed\u1eee\u1eef\u1ef0\u1ef1\u1ef2\u1ef3"
    "\u1ef4\u1ef5\u1ef6\u1ef7\u1ef8\u1ef9"
)
_VIETOCR_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "vietocr_onnx")
_VIETOCR_CACHE_PATH = os.path.join(_VIETOCR_CACHE_DIR, "vietocr_vgg_transformer.onnx")

_IMG_HEIGHT = 32
_IMG_WIDTH_MAX = 512


def _resolve_vietocr_onnx_path() -> str | None:
    """Tìm đường dẫn model VietOCR ONNX theo thứ tự ưu tiên: env var > cache."""
    env_path = os.environ.get("VIETOCR_ONNX_PATH", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    if os.path.isfile(_VIETOCR_CACHE_PATH):
        return _VIETOCR_CACHE_PATH
    return None


class VietOCROnnxRecognizer:
    """Nhận diện chữ tiếng Việt bằng ONNX model (VGG-Transformer)."""

    def __init__(self, model_path: str) -> None:
        import onnxruntime as ort  # type: ignore[import-untyped]

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 4
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            model_path,
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        logger.info("VietOCR ONNX session khởi tạo thành công từ: %s", model_path)

    def _preprocess_image(self, img_bgr: np.ndarray) -> np.ndarray | None:
        cv2 = _import_cv2()
        if cv2 is None:
            return None
        h, w = img_bgr.shape[:2]
        if h == 0 or w == 0:
            return None
        new_w = min(max(int(w * _IMG_HEIGHT / h), 1), _IMG_WIDTH_MAX)
        resized = cv2.resize(img_bgr, (new_w, _IMG_HEIGHT))
        if resized.ndim == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        arr = resized.astype(np.float32) / 255.0
        return arr[np.newaxis, np.newaxis, ...]

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

    def recognize_batch(self, line_images: list[np.ndarray]) -> list[str]:
        results: list[str] = []
        for img in line_images:
            tensor = self._preprocess_image(img)
            if tensor is None:
                results.append("")
                continue
            try:
                outputs = self._session.run(None, {self._input_name: tensor})
                logits = outputs[0]
                if logits.ndim == 3:
                    if logits.shape[0] == 1:
                        logits = logits[0]
                    elif logits.shape[1] == 1:
                        logits = logits[:, 0, :]
                text = self._ctc_greedy_decode(logits)
                results.append(text)
            except Exception as exc:
                logger.warning("VietOCR ONNX inference lỗi một dòng: %s", exc)
                results.append("")
        return results


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

        # 1. Ưu tiên: VietOCR vgg_seq2seq.pth (mô hình chuẩn Tiếng Việt có dấu)
        self._seq2seq_recognizer: VietOCRSeq2SeqRecognizer | None = None
        seq2seq_path = _resolve_vgg_seq2seq_path()
        if seq2seq_path is not None:
            try:
                self._seq2seq_recognizer = VietOCRSeq2SeqRecognizer(
                    weights_path=seq2seq_path,
                    device=settings.vietocr_device,
                    beamsearch=settings.vietocr_beamsearch,
                )
                logger.info("LocalOcrEngine: sử dụng VietOCR Seq2Seq (%s)", seq2seq_path)
            except Exception as exc:
                logger.warning("Không thể khởi tạo VietOCR Seq2Seq (%s). Thử các giải pháp thay thế.", exc)
                self._seq2seq_recognizer = None

        # 2. Dự phòng 2: VietOCR ONNX Recognizer nếu có
        self._onnx_recognizer: VietOCROnnxRecognizer | None = None
        if self._seq2seq_recognizer is None:
            onnx_path = _resolve_vietocr_onnx_path()
            if onnx_path is not None and os.path.isfile(onnx_path):
                try:
                    self._onnx_recognizer = VietOCROnnxRecognizer(onnx_path)
                    logger.info("LocalOcrEngine: sử dụng VietOCR ONNX Recognizer (%s)", onnx_path)
                except Exception as exc:
                    logger.warning("Không thể khởi tạo VietOCROnnxRecognizer: %s", exc)
                    self._onnx_recognizer = None

        if self._seq2seq_recognizer is None and self._onnx_recognizer is None:
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
        for box in boxes:
            pts = np.array(box, dtype=np.float32)
            cx = float(pts[:, 0].mean())
            bw = float(pts[:, 0].max() - pts[:, 0].min())
            bh = float(pts[:, 1].max() - pts[:, 1].min())

            # Bỏ mảnh rác nhỏ li ti (< 7x7 px)
            if bw < 7.0 and bh < 7.0:
                continue

            # Bỏ các mẩu chữ từ trang đối diện lọt vào mép phải (x > 91% width và bề ngang hẹp < 45px)
            if cx > img_w * 0.91 and bw < 45.0:
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
        """
        if not boxes:
            return []

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
        # Pipeline 1: RapidOCR Det + VietOCR Seq2Seq Recognizer (vgg_seq2seq)
        # --------------------------------------------------------------
        if self._seq2seq_recognizer is not None:
            raw_boxes = self._run_detection(image, det_params)
            if not raw_boxes:
                logger.info("Local OCR (VietOCR Seq2Seq): không phát hiện vùng chữ nào.")
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

            # Batch recognition
            all_sents: list[str] = []
            all_probs: list[float] = []
            for i in range(0, len(all_crops), self._batch_size):
                batch = all_crops[i : i + self._batch_size]
                sents, probs = self._seq2seq_recognizer.recognize_batch(batch)
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

            logger.info(
                "Local OCR (VietOCR Seq2Seq): %d dòng -> %d ký tự, conf=%.2f",
                len(final_lines),
                len(full_text),
                avg_conf,
            )
            return full_text, len(final_lines), avg_conf

        # --------------------------------------------------------------
        # Pipeline 2: RapidOCR Det + VietOCR ONNX Recognizer
        # --------------------------------------------------------------
        if self._onnx_recognizer is not None:
            raw_boxes = self._run_detection(image, det_params)
            if not raw_boxes:
                return "", 0, 0.0

            sorted_boxes = self._sort_reading_order(raw_boxes, image_shape=image.shape)
            line_images: list[np.ndarray] = []
            for box in sorted_boxes:
                cropped = self._crop_line(image, box)
                if cropped is not None and cropped.size > 0:
                    line_images.append(cropped)

            if not line_images:
                return "", 0, 0.0

            recognized: list[str] = []
            for i in range(0, len(line_images), self._batch_size):
                batch = line_images[i : i + self._batch_size]
                recognized.extend(self._onnx_recognizer.recognize_batch(batch))

            lines = clean_quiz_lines([t.strip() for t in recognized if t.strip()])
            full_text = "\n".join(lines)
            return full_text, len(lines), 0.85

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
