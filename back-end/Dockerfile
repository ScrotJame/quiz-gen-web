# ==============================================================================
# Stage 1: Builder (Install runtime dependencies into virtual environment)
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt build-essential để biên dịch các package native C/C++ nếu cần
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Khởi tạo virtual environment sạch
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements-runtime.txt .

# Cài đặt runtime dependencies (ONNX Runtime, FastAPI, RapidOCR, OpenCV - KHÔNG cài PyTorch/VietOCR)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-runtime.txt

# ==============================================================================
# Stage 2: Production (Minimal runtime image, ONNX Runtime inference)
# ==============================================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết cho OpenCV headless và curl cho healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sao chép virtual environment từ builder (hoàn toàn không có torch / torchvision / vietocr)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tạo non-root user an toàn
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/src && \
    chown -R appuser:appuser /app

# Sao chép requirements và mã nguồn (chứa 3 file .onnx và vocab_chars.txt trong src/models/vietocr/)
COPY --chown=appuser:appuser requirements-runtime.txt ./
COPY --chown=appuser:appuser src/ ./src/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]