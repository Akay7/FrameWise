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
ENV CAPTION_PROVIDER=gemini

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

# Optional, OFF BY DEFAULT: bake an API key into the image for judges that
# cannot inject environment variables. Prefer passing the key at run time
# (docker run -e GEMINI_API_KEY=...). main.py loads this file into the
# environment at startup. Example:
#   docker build --build-arg BAKE_PROVIDER_KEY_ENV=GEMINI_API_KEY \
#                --build-arg BAKE_PROVIDER_KEY=sk-... .
ARG BAKE_PROVIDER_KEY_ENV=""
ARG BAKE_PROVIDER_KEY=""
RUN if [ -n "$BAKE_PROVIDER_KEY_ENV" ] && [ -n "$BAKE_PROVIDER_KEY" ]; then \
        printf '%s=%s\n' "$BAKE_PROVIDER_KEY_ENV" "$BAKE_PROVIDER_KEY" \
            > /app/.baked_env; \
    fi
ENV BAKED_ENV_FILE=/app/.baked_env

ENTRYPOINT ["python3", "main.py"]
