# Track 2 — Video Captioning Agent (AMD ROCm, linux/amd64).
#
# Slim Ubuntu base + torch from the ROCm wheel index (self-contained ROCm
# runtime) rather than the full rocm/pytorch image, which alone can exceed the
# 10 GB compressed cap. Model weights are baked in for zero network dependency
# at evaluation time.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false

# ROCm wheel channel — override at build time to match the host's ROCm version:
#   docker build --build-arg ROCM_INDEX=https://download.pytorch.org/whl/rocm6.3 .
ARG ROCM_INDEX=https://download.pytorch.org/whl/rocm6.2
ARG MODEL_ID=Qwen/Qwen2.5-VL-3B-Instruct

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        ffmpeg libgl1 libglib2.0-0 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch / torchvision from the ROCm index (NOT PyPI, which would be CUDA/CPU).
RUN pip3 install --no-cache-dir --index-url ${ROCM_INDEX} \
        torch torchvision

# Application dependencies.
COPY pyproject.toml ./
RUN pip3 install --no-cache-dir \
        "transformers>=4.49.0" \
        qwen-vl-utils \
        accelerate \
        sentencepiece \
        Pillow \
        requests \
        huggingface-hub

# Bake model weights into the image (no GPU needed to just download).
RUN python3 -c "\
from huggingface_hub import snapshot_download; \
from transformers import AutoProcessor; \
mid='${MODEL_ID}'; \
print('Downloading', mid); \
snapshot_download(mid); \
AutoProcessor.from_pretrained(mid); \
print('Weights cached under', '${HF_HOME}')"

COPY main.py validation.py ./

RUN mkdir -p /input /output

ENV MODEL_ID=${MODEL_ID}

ENTRYPOINT ["python3", "main.py"]
