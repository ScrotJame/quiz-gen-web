# ==============================================================================
# Stage 1: Builder (Install dependencies into virtual environment)
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Cài đặt trước PyTorch CPU-only wheel để tránh tải bản CUDA nặng 1.2GB+
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Runtime (Minimal production container)
# ==============================================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết cho OpenCV headless và curl cho healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sao chép virtual environment từ builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tạo non-root user an toàn
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/src && \
    chown -R appuser:appuser /app

# Sao chép mã nguồn ứng dụng
COPY --chown=appuser:appuser src/ ./src/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]