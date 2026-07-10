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
- Caption provider is selected via the same `CAPTION_PROVIDER` /
  `*_API_KEY` environment variables the container already uses — the app
  does not introduce a new provider path, it reuses `providers.py` directly.
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
  `media.py` helpers for video download/frame extraction); no changes to
  `main.py`, `providers.py`, or `validation.py`.
- **Dependencies**: add `gradio` to `pyproject.toml` (demo-only dependency)
  and a `requirements.txt` for the demo's own Docker build; the graded
  `Dockerfile`/image is unaffected — it does not COPY `app.py` or
  `requirements.txt`.
- **Hosting**: new `Dockerfile.demo` + `render.yaml`, deployed as a Render
  free web service, requires the same `CAPTION_PROVIDER` / provider API key
  set as Render environment variables/secrets.
- **Docs**: `README.md` gains a Demo section with the Render URL and usage
  instructions for both input modes.
