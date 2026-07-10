## Context

The container pipeline (`main.py` + `providers.py` + `media.py`) is a
batch job: it reads `/input/tasks.json`, downloads each clip, calls the
selected external vision provider (Gemini/OpenAI/Anthropic), and writes
`/output/results.json`. It has no HTTP surface and assumes the caller can
mount files and set env vars — fine for the grading harness, not something
a judge can click into. The hackathon submission form has two required
fields, **Demo Application Platform** and **Application URL**, that this
change exists to satisfy: a live app, and the URL where it's reachable.

## Goals / Non-Goals

**Goals:**
- Give judges a URL that runs the real pipeline (same `providers.py`
  adapters, same output contract) against a video they choose.
- Support both interaction shapes the pipeline already supports: one clip
  at a time, and a batch `tasks.json` file shaped like `sample_tasks.json`.
- Reuse existing code paths (`providers.get_provider`, `media.py` helpers)
  instead of re-implementing captioning logic in the app layer.
- Ship on a platform that's free and fast to stand up mid-hackathon.

**Non-Goals:**
- No new caption provider, prompt, or output format — the app is a thin
  UI over the existing `providers.py`/`media.py` contract.
- No auth, multi-tenancy, key storage, or persistence — each visitor's key
  lives only in that request's memory for the duration of the call.
- No change to the Docker image used for grading; the demo deployment is a
  separate artifact from `ghcr.io/akay7/amd-act2-track2-video_captioning_agent`.

## Decisions

- **Framework: Gradio.** Minimal boilerplate for file-upload + dropdown +
  JSON/table output, native Hugging Face Spaces support (push-to-deploy,
  free CPU tier), and idiomatic for "AI demo" hackathon submissions.
  Alternative considered: Streamlit — comparable effort, but Spaces'
  Gradio SDK has more direct file-upload ergonomics for this use case.
- **Reuse `providers.get_provider()` and `media.py` directly**, rather than
  shelling out to `main.py` as a subprocess. The app imports the same
  Python modules the container uses, so behavior (prompt, styles, retries)
  stays identical between the graded container and the demo by
  construction — no duplicated logic to drift out of sync.
- **Two tabs, one pipeline.** Single-video tab builds a one-task list
  in-memory (`[{"task_id": "demo", "video_url": ..., "styles": [...]}]`,
  or a locally-saved upload path in place of `video_url`) and runs it
  through the same per-task loop `main.py` uses. Batch tab parses an
  uploaded `tasks.json` with the same shape as `sample_tasks.json` and
  runs every task through that loop, rendering a table plus a downloadable
  `results.json` matching the container's output contract.
- **Provider + API key supplied by the visitor via the UI**, not a
  server-side secret. A provider dropdown and a password-style key field
  are added to both tabs; `providers.get_provider(name, api_key)` is
  called per-request with that key, and the key is never read from or
  written to server environment variables, logs, or disk. This replaces
  the original "environment/Space secrets, no UI key control" decision —
  that design centralized cost/quota risk on one shared key absorbing
  every visitor's usage; per-visitor keys remove that risk entirely and
  also mean the Render service needs no provider secret configured at all.
  Trade-off: every visitor must have their own provider API key to try the
  demo, which is more friction than a pre-configured shared key.
  `providers.py`'s adapters gain optional `api_key`/`base_url`/`model`
  parameters, defaulting to the existing env-var lookups — `main.py`/the
  container behavior is unchanged.
- **`openai` provider gets optional Base URL / Model fields in the UI.**
  `OpenAIProvider` already supports `OPENAI_BASE_URL` (point at any
  OpenAI-compatible server, e.g. local Lemonade) and `OPENAI_MODEL`; the
  demo exposes both as optional textboxes shown only when `openai` is the
  selected provider, passed through to `get_provider(..., base_url=,
  model=)`. When a Base URL is set, the API key field becomes optional in
  the UI too — same rule the container already applies (`_require_key` is
  skipped for a configured `base_url`, since local servers don't need a
  real key).
- **Local file upload support**: since the existing pipeline expects a
  `video_url` it can download, an uploaded file is saved to a temp path
  and passed through as a local path (`media.py`'s download step already
  needs to special-case local paths vs. HTTP URLs) rather than requiring
  every demo video to be pre-hosted.
- **Deploy target: Render**, free web service plan, built from a demo-only
  `Dockerfile.demo` (no local inference runs there either — it only calls
  the external provider API, same as the container). Originally targeted
  Hugging Face Spaces, but HF now requires a paid plan for compute-backed
  (Gradio/Docker) Spaces on the namespace available for this project;
  Render's free tier needs no payment method and reuses the same
  Docker-based deployment shape as the graded container, just with a
  different entrypoint (`app.py` instead of `main.py`) and a bound HTTP
  port instead of file I/O. Trade-off: Render's free tier spins the service
  down after ~15 minutes idle, adding a cold-start delay (usually
  30-50s) on the first request after a gap — acceptable for a
  judge opening the link once, documented in the README.

## Risks / Trade-offs

- [A visitor-entered API key leaks via server logs, error messages, or a
  temp file] → Never log the raw key; pass it in-memory straight to the
  SDK client constructor for the duration of the request only; provider
  error messages surfaced to the UI are the SDK's own exception text,
  which does not include the key value.
- [Large video uploads or long batch files could exceed the free-tier
  request timeout / resource limits] → Cap upload size and batch task
  count in the UI, and surface the provider's per-clip timeout
  (`REQUEST_TIMEOUT`) as user-facing progress rather than a silent hang.
  The per-session request cap now guards shared CPU/compute on the free
  Render instance rather than a shared provider key (there isn't one).
- [Demo pipeline drifts from the graded container if someone edits `app.py`
  copies of provider logic instead of the shared modules] → Enforced by
  the design decision to import `providers.py`/`media.py` directly rather
  than reimplementing; no fork of the captioning logic.
- [Render free-tier cold start adds latency on first judge visit after an
  idle period] → Accept as a known limitation of the free plan; document
  expected first-load time in the README Demo section.

## Migration Plan

1. Add `app.py` at repo root importing `providers.py` / `media.py`.
2. Add `gradio` to `pyproject.toml` (demo dependency) and `requirements.txt`
   for the demo's own Docker build.
3. Add `Dockerfile.demo` (installs `ffmpeg` + `requirements.txt`, runs
   `app.py` bound to `$PORT`) and `render.yaml` describing the free web
   service.
4. Create the Render service from this repo (Docker runtime, free plan) —
   no provider secret to configure; visitors bring their own key.
5. Smoke-test both tabs against the Render URL (single video, and
   `sample_tasks.json` through the batch tab), each with a real user-supplied
   key.
6. Document the Render URL and usage in `README.md`, including that
   visitors need their own provider API key.

No rollback complexity: the Render service is additive infrastructure, and
deleting it or taking it offline has no effect on the graded container
image.

## Open Questions

- None outstanding — moving to visitor-supplied keys resolved the prior
  open question of which shared key/budget to use for the public demo.
