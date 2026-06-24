FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install system dependencies:
# - ffmpeg for video processing
# - libgl/libglib for opencv-python-headless
# - g++ for native extensions required by insightface during uv sync
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 g++ && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Install deps first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

EXPOSE 18765

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

# task_manager / confirm flow依赖进程内状态，默认保持单 worker，避免恢复/取消流程失真。
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-18765} --workers ${WEB_CONCURRENCY:-1}"]
