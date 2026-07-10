## 1. Setup

- [x] 1.1 Add `gradio` to `pyproject.toml` as a dependency
- [x] 1.2 Create `app.py` at repo root importing `providers.get_provider`, `providers.ALL_STYLES`, and `media.py`'s download/probe helpers

## 2. Shared pipeline helper

- [x] 2.1 Extract/reuse a `run_tasks(tasks: list[dict], provider) -> list[dict]` helper (mirroring `main.py`'s per-task loop) that `app.py` and `main.py` both call, so the demo and the container never fork captioning logic
- [x] 2.2 Handle local file paths (from Gradio uploads) alongside remote `video_url`s in the download step
- [x] 2.3 Load the provider once at app startup via `get_provider()`; fail fast with a visible config error if the key/provider is invalid

## 3. Single-video tab

- [x] 3.1 Build UI: file upload, video URL text input (mutually exclusive with upload), style multi-select, submit button, per-style caption output
- [x] 3.2 Wire submit to build a one-task list and call the shared pipeline helper
- [x] 3.3 Validate at least one style is selected before submitting; show inline error otherwise
- [x] 3.4 Show a progress/loading indicator while the provider call is in flight

## 4. Batch tasks-file tab

- [x] 4.1 Build UI: `tasks.json` file upload, submit button, results table, JSON download button
- [x] 4.2 Parse and validate the uploaded file (valid JSON array, each entry has `video_url`); surface a clear error for malformed input without calling the provider
- [x] 4.3 Wire submit to run all parsed tasks through the shared pipeline helper and render one row per `task_id` with each style's caption
- [x] 4.4 Serialize results to the container's output-contract JSON shape and offer as a downloadable file
- [x] 4.5 Verify against `sample_tasks.json` end-to-end

## 5. Guardrails

- [x] 5.1 Cap uploaded video size and batch task count in the UI to avoid exceeding Spaces' free-tier request limits
- [x] 5.2 Add a simple per-session request cap to protect the shared demo provider key from quota exhaustion

## 6. Deploy to Render

- [x] 6.1 Add `Dockerfile.demo` (ffmpeg + `requirements.txt`, runs `app.py` bound to `$PORT`) and `render.yaml` (free web service, Docker runtime)
- [x] 6.2 Add `requirements.txt` covering `gradio` plus the provider SDKs used by `providers.py`
- [ ] 6.3 Create the Render service from this repo and set `CAPTION_PROVIDER` / the matching `<PROVIDER>_API_KEY` as environment variables in the Render dashboard — **manual**: needs a Render account/login, not available in this environment
- [ ] 6.4 Confirm the service builds and starts on Render — **manual**: needs Render access

## 7. Verify and document

- [ ] 7.1 Smoke-test the single-video tab against the live Render URL (upload path and URL path) — blocked on 6.3/6.4
- [ ] 7.2 Smoke-test the batch tab against the live Render URL using `sample_tasks.json` — blocked on 6.3/6.4 (equivalent logic already verified locally with a stub provider against `sample_tasks.json`, output passed `validation.validate_results`)
- [ ] 7.3 Add a "Demo" section to `README.md` with the Render URL and usage instructions for both tabs — section added with local-run and deploy instructions; **swap in the real Render URL once 6.3–6.4 are done**
- [ ] 7.4 Record the Application URL and Demo Application Platform ("Render") for the hackathon submission form — blocked on 6.3
