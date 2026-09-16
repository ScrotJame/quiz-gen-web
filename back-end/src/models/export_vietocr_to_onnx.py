"""
Export vgg_seq2seq (vietocr) sang 3 file ONNX: cnn.onnx, encoder.onnx, decoder.onnx
Chạy trên máy dev có torch + vietocr cài sẵn (KHÔNG cần chạy trong Docker production).
"""

import os
import sys
import torch
from vietocr.tool.config import Cfg
from vietocr.tool.translate import build_model

# ====== 0. Load model gốc từ file .pth ======
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHT_PATH = os.environ.get(
    "WEIGHT_PATH", os.path.join(SCRIPT_DIR, "vietocr", "vgg_seq2seq.pth")
)
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(SCRIPT_DIR, "vietocr"))
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Loading weights from: {WEIGHT_PATH}")
print(f"Output directory: {OUT_DIR}")

config = Cfg.load_config_from_name("vgg_seq2seq")
config["weights"] = WEIGHT_PATH
config["cnn"]["pretrained"] = False
config["device"] = "cpu"

model, vocab = build_model(config)
model.load_state_dict(torch.load(WEIGHT_PATH, map_location="cpu"))
model.eval()

cnn = model.cnn
encoder = model.transformer.encoder
decoder = model.transformer.decoder

HIDDEN = 256  # theo config: encoder_hidden = decoder_hidden = 256

class CNNWrapper(torch.nn.Module):
    """Bọc CNN để sửa lỗi permute(-1, 0, 1) -> permute(2, 0, 1) của VietOCR VGG backbone khi export ONNX."""

    def __init__(self, cnn_model):
        super().__init__()
        self.cnn = cnn_model

    def forward(self, x):
        conv = self.cnn.model.features(x)
        conv = self.cnn.model.dropout(conv)
        conv = self.cnn.model.last_conv_1x1(conv)
        conv = conv.transpose(-1, -2)
        conv = conv.flatten(2)
        return conv.permute(2, 0, 1)


wrapped_cnn = CNNWrapper(cnn)

# ====== 1. Export CNN ======
# Input: ảnh (batch, 3, H=32, W). H cố định 32, W linh hoạt theo độ dài text.
# Output CNN của vietocr đã tự permute về (seq_len, batch, 256) sẵn cho GRU encoder.
dummy_img = torch.randn(1, 3, 32, 128)

cnn_path = os.path.join(OUT_DIR, "cnn.onnx")
torch.onnx.export(
    wrapped_cnn,
    dummy_img,
    cnn_path,
    input_names=["img"],
    output_names=["src"],
    dynamic_axes={
        "img": {0: "batch", 3: "width"},
        "src": {0: "seq_len", 1: "batch"},
    },
    opset_version=14,
    dynamo=False,
)
print("✅ Exported cnn.onnx")

# ====== 2. Export Encoder (chạy 1 lần duy nhất trên toàn bộ feature map) ======
with torch.no_grad():
    src = cnn(dummy_img)  # (seq_len, batch, 256) — dùng làm dummy input thật cho encoder

encoder_path = os.path.join(OUT_DIR, "encoder.onnx")
torch.onnx.export(
    encoder,
    src,
    encoder_path,
    input_names=["src"],
    output_names=["encoder_outputs", "hidden"],
    dynamic_axes={
        "src": {0: "seq_len", 1: "batch"},
        "encoder_outputs": {0: "seq_len", 1: "batch"},
    },
    opset_version=14,
    dynamo=False,
)
print("✅ Exported encoder.onnx")

# ====== 3. Export Decoder (CHỈ 1 bước — vòng lặp sinh ký tự viết ở ngoài) ======
with torch.no_grad():
    encoder_outputs, hidden = encoder(src)

tgt_input = torch.LongTensor([1])  # token <sos>, batch=1

decoder_path = os.path.join(OUT_DIR, "decoder.onnx")
torch.onnx.export(
    decoder,
    (tgt_input, hidden, encoder_outputs),
    decoder_path,
    input_names=["tgt_input", "hidden", "encoder_outputs"],
    output_names=["prediction", "hidden_out", "attn"],
    dynamic_axes={
        "encoder_outputs": {0: "seq_len", 1: "batch"},
        "attn": {1: "seq_len"},
    },
    opset_version=14,
    dynamo=False,
)
print("✅ Exported decoder.onnx")

# ====== 4. Export vocab_chars.txt ======
vocab_path = os.path.join(OUT_DIR, "vocab_chars.txt")
with open(vocab_path, "w", encoding="utf-8") as f:
    f.write(vocab.chars)
print(f"✅ Exported vocab_chars.txt ({len(vocab.chars)} characters)")

print("\nXong! 4 file cnn.onnx, encoder.onnx, decoder.onnx, vocab_chars.txt đã sẵn sàng.")