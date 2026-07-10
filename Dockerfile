# Track 2 — Video Captioning Agent (linux/amd64).
#
# Pure external captioning: the container calls a hosted vision model, so it
# ships no model weights and no GPU/torch stack. A slim Python base + ffmpeg is
# all it needs, keeping the image tiny and cold-start well under 60s.
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Caption provider selected at runtime: gemini | openai | anthropic.
# Override at build time with: docker build --build-arg CAPTION_PROVIDER=openai .
ARG CAPTION_PROVIDER=gemini
ENV CAPTION_PROVIDER=${CAPTION_PROVIDER}

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip3 install --no-cache-dir \
        requests \
        google-genai \
        openai \
        anthropic

COPY main.py media.py providers.py validation.py ./

RUN mkdir -p /input /output

# Optional, OFF BY DEFAULT: bake provider settings into the image for judges
# that cannot inject environment variables. Prefer passing these at run time
# (docker run -e OPENAI_API_KEY=...) instead. main.py loads this file into the
# environment at startup (runtime env vars still win). Example:
#   docker build --build-arg BAKE_PROVIDER_KEY_ENV=GEMINI_API_KEY \
#                --build-arg BAKE_PROVIDER_KEY=sk-... .
# For the openai provider, the base URL and model can be baked too:
#   docker build --build-arg CAPTION_PROVIDER=openai \
#                --build-arg OPENAI_API_KEY=sk-... \
#                --build-arg OPENAI_BASE_URL=https://api.openai.com/v1 \
#                --build-arg OPENAI_MODEL=gpt-4o .
ARG BAKE_PROVIDER_KEY_ENV=""
ARG BAKE_PROVIDER_KEY=""
ARG OPENAI_API_KEY=""
ARG OPENAI_BASE_URL=""
ARG OPENAI_MODEL=""
RUN rm -f /app/.baked_env \
    && if [ -n "$BAKE_PROVIDER_KEY_ENV" ] && [ -n "$BAKE_PROVIDER_KEY" ]; then \
        printf '%s=%s\n' "$BAKE_PROVIDER_KEY_ENV" "$BAKE_PROVIDER_KEY" \
            >> /app/.baked_env; \
    fi \
    && if [ -n "$OPENAI_API_KEY" ]; then \
        printf 'OPENAI_API_KEY=%s\n' "$OPENAI_API_KEY" >> /app/.baked_env; \
    fi \
    && if [ -n "$OPENAI_BASE_URL" ]; then \
        printf 'OPENAI_BASE_URL=%s\n' "$OPENAI_BASE_URL" >> /app/.baked_env; \
    fi \
    && if [ -n "$OPENAI_MODEL" ]; then \
        printf 'OPENAI_MODEL=%s\n' "$OPENAI_MODEL" >> /app/.baked_env; \
    fi
ENV BAKED_ENV_FILE=/app/.baked_env

ENTRYPOINT ["python3", "main.py"]
