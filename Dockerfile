FROM python:3.11-slim

# Security: run as non-root
RUN groupadd -r george && useradd -r -g george george

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Data directories
RUN mkdir -p /data/video_exports /data/logs && \
    chown -R george:george /app /data

USER george

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from config.settings import get_settings; get_settings()" || exit 1

CMD ["python", "-m", "scheduler.weekly_cycle"]
