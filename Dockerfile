# Production-friendly Dockerfile (multi-stage for smaller final image)
FROM python:3.10-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime system deps (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      ffmpeg \
      libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ---------- Build stage ----------
FROM base AS build
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc make python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt /build/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip wheel --wheel-dir /wheels -r /build/requirements.txt

# ---------- Final image ----------
FROM base AS final
WORKDIR /app

COPY --from=build /wheels /wheels
COPY --from=build /build/requirements.txt /build/requirements.txt
RUN pip install --no-index --find-links=/wheels -r /build/requirements.txt

COPY . /app

RUN mkdir -p /data/proofs && chown -R root:root /data/proofs

EXPOSE 7860
ENV GRADIO_SERVER_PORT=7860
ENV GRADIO_SERVER_NAME=0.0.0.0

# Entrypoint: Using app.py to launch both FastAPI (for metrics/smoke tests) and Gradio
# (Replaced main_ui.py with app.py to ensure Metrics & API endpoints are available for production)
CMD ["python", "app.py"]
