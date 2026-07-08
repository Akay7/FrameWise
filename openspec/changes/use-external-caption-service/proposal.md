## Why

The judge VM's hardware is unknown, so betting the whole entry on a local
GPU model (Qwen2.5-VL on ROCm) is a single point of failure — a missing or
incompatible GPU means every caption is empty and the score is zero. The
hackathon rules permit calling external services, and hosted vision models are
both stronger at captioning and independent of the judge's hardware. Moving to
an external captioning API removes the hardware risk, shrinks the image well
under the 10 GB cap, and lets the container be ready in seconds.

## What Changes

- **BREAKING**: Remove the local Qwen2.5-VL model, the ROCm/torch dependency
  stack, and the baked-in model weights. The container no longer performs
  on-device inference.
- Add a **provider-agnostic caption client** with adapters for Google Gemini,
  OpenAI, and Anthropic, selected at runtime via a `CAPTION_PROVIDER` env var.
- Each adapter takes the clip (native video where the provider supports it,
  otherwise sampled frames) plus the requested styles and returns one caption
  per style in a single call.
- **Credentials via environment variables** (e.g. `GEMINI_API_KEY`), read at
  runtime — no secrets baked into the image by default, with a documented
  optional build-arg path to embed one if a judge cannot inject env vars.
- **Pure external, no local fallback**: if the provider is unreachable or the
  key is missing, the run fails loudly rather than silently degrading. The
  output-contract self-check still guarantees well-formed JSON for whatever
  captions were produced.
- Rebuild the Dockerfile on a slim Python base (no ROCm wheels, no GPU
  libraries), dramatically reducing image size and startup time.
- Update `pyproject.toml`, `README.md`, and the e2e test to the new
  provider/credentials model.

## Capabilities

### New Capabilities
- `external-caption-provider`: A pluggable client that generates per-style
  captions for a video clip by calling a hosted vision model. Covers provider
  selection, credential loading, per-clip request construction (native video or
  sampled frames), one-call multi-style output, and error handling when the
  service or key is unavailable.

### Modified Capabilities
<!-- No existing archived specs; the container-output-contract behavior is
     unchanged and continues to be enforced by validation.py. -->

## Impact

- **Code**: `main.py` (swap local inference for provider client), new
  `providers.py` (adapter interface + Gemini/OpenAI/Anthropic implementations),
  `validation.py` unchanged.
- **Dependencies**: remove `torch`, `torchvision`, `transformers`,
  `qwen-vl-utils`, `accelerate`, `sentencepiece`; add the chosen provider SDKs
  (`google-genai`, `openai`, `anthropic`) — all lightweight.
- **Dockerfile**: slim Python base, no ROCm index, no model download step.
- **Runtime contract**: now requires network egress and a valid API key at
  evaluation time (documented prerequisite); image size and cold-start drop
  sharply.
- **Docs/tests**: `README.md` provider/credentials section; `tests/run_e2e.py`
  passes the key through and no longer needs GPU flags.
