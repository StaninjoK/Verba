# Verba – single container: FastAPI backend + exported frontend + local Whisper.
# Build:  docker build -t verba .
# Run:    docker run -p 8080:8080 -e VERBA_AUTH_PASSWORD=... -v verba-data:/data verba

# ---- 1. Frontend as static files -------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build:static

# ---- 2. Runtime --------------------------------------------------------------
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-whisper.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-whisper.txt

# Whisper model is baked into the image at build time (free download from Hugging Face).
# "base" (~145 MB) fits small instances; use "small" with ≥2 GB RAM.
ARG WHISPER_MODEL=base
RUN python -c "from faster_whisper import download_model; download_model('${WHISPER_MODEL}', output_dir='/models/faster-whisper-${WHISPER_MODEL}')"

COPY backend/verba ./verba
COPY --from=web /web/out /app/static

RUN useradd --system --uid 10001 verba && mkdir -p /data && chown verba /data
USER verba

ENV VERBA_HOST=0.0.0.0 \
    VERBA_PORT=8080 \
    VERBA_STATIC_DIR=/app/static \
    VERBA_DATA_DIR=/data \
    VERBA_WHISPER_MODEL=${WHISPER_MODEL} \
    VERBA_WHISPER_MODEL_DIR=/models \
    VERBA_ALLOWED_PROVIDERS=faster-whisper \
    VERBA_REQUIRE_AUTH=true \
    VERBA_MAX_UPLOAD_MB=200 \
    VERBA_MAX_STORAGE_MB=3000 \
    VERBA_MAX_MEDIA_DURATION_MIN=120 \
    VERBA_CORS_ORIGINS= \
    PYTHONUNBUFFERED=1

EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"VERBA_PORT\",\"8080\")}/api/health')"
CMD ["python", "-m", "verba.main"]
