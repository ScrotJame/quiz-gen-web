FROM python:3.11-slim

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src/ ./src/

RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]