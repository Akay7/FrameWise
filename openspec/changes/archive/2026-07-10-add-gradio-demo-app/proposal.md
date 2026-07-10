## Why

The hackathon submission form requires a **Demo Application Platform** and an
**Application URL** — a live, clickable demo judges can open without pulling
the Docker image or wiring up API keys themselves. Today the agent is a
batch CLI/container (`main.py` reading `/input/tasks.json`, writing
`/output/results.json`); there is no interactive surface to submit as the demo.

## What Changes

- Add a **Gradio web app** (`app.py`) that wraps the existing
  `providers.get_provider()` / caption pipeline with two input modes:
  - **Single video**: upload a video file (or paste a URL) and pick one or
    more caption styles; runs one clip through the pipeline and displays the
    per-style captions.
  - **Batch tasks file**: upload a `tasks.json` in the same shape as
    `sample_tasks.json` (`task_id`, `video_url`, `styles`); runs every task
    through the pipeline and displays a results table (same shape as
    `results.json`), downloadable as JSON.
- **Each visitor supplies their own API key.** The UI adds a provider
  dropdown (gemini/openai/anthropic) and a password-style API key field;
  the app calls `providers.get_provider(name, api_key)` with that
  per-request key and never reads a provider key from server environment
  variables. This removes the original design's shared-key risk (one
  public key absorbing every visitor's usage/cost) entirely, at the cost of
  requiring each visitor to bring their own key. `providers.py` gains
  optional `api_key`/`base_url`/`model` parameters on `get_provider`/each
  adapter, defaulting to the existing env-var lookups so `main.py`/the
  container are unaffected.
- **When `openai` is selected, expose optional Base URL and Model fields**
  (mirroring the existing `OPENAI_BASE_URL`/`OPENAI_MODEL` env vars). This
  lets a visitor point the demo at their own OpenAI-compatible endpoint
  (e.g. a locally-run Lemonade/vLLM/LM Studio server they've exposed) —
  and per the existing adapter logic, the API key becomes optional in that
  case (local servers accept a placeholder key).
- Deploy the app to **Render** (free web service, Docker) as the demo
  platform; the service's public URL becomes the submission's Application URL.
  (Hugging Face Spaces was the original target, but its free tier now gates
  Gradio/Docker Spaces behind a paid plan — Render's free tier needs no card
  and runs our existing Docker-based pipeline unchanged.)
- Update `README.md` with a "Demo" section documenting the app and the
  hosted URL.

## Capabilities

### New Capabilities
- `demo-web-app`: An interactive Gradio UI for trying the captioning
  pipeline without Docker — single-video mode and batch-tasks-file mode,
  both reusing the existing provider client and output contract.

### Modified Capabilities
<!-- No existing archived specs; main.py/providers.py behavior and the
     container output contract are unchanged — the demo app calls the same
     provider client, it does not alter it. -->

## Impact

- **Code**: new `app.py` (Gradio UI, imports `providers.py` and reuses
  `media.py` helpers for video download/frame extraction); `providers.py`
  gains an optional `api_key` parameter (backward-compatible — `main.py`
  and `validation.py` are otherwise unchanged).
- **Dependencies**: add `gradio` to `pyproject.toml` (demo-only dependency)
  and a `requirements.txt` for the demo's own Docker build; the graded
  `Dockerfile`/image is unaffected — it does not COPY `app.py` or
  `requirements.txt`.
- **Hosting**: new `Dockerfile.demo` + `render.yaml`, deployed as a Render
  free web service. No provider API key needs to be configured on Render —
  visitors supply their own key per request, so the service itself holds
  no secrets.
- **Docs**: `README.md` gains a Demo section with the Render URL, usage
  instructions for both input modes, and a note that visitors need their
  own provider API key.
