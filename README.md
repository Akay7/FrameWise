# FrameWise

*Track 2 — Video Captioning Agent*

Reads `/input/tasks.json`, generates a caption per requested style for every clip
by calling a hosted vision model, and writes `/output/results.json`. No local
model and no GPU are required — the container is a slim Python image that runs
anywhere with network access.

## Demo

**Live demo:** [framewise-demo.onrender.com](https://framewise-demo.onrender.com/)

`app.py` is a [Gradio](https://gradio.app) UI over the same pipeline the
container uses (`providers.get_provider`, `main.run_tasks`) — no captioning
logic is duplicated. Two tabs:

- **Single video**: upload a video file or paste a video URL, pick one or
  more caption styles, and see the generated caption per style.
- **Batch tasks file**: upload a `tasks.json` shaped like `sample_tasks.json`
  (`task_id`, `video_url`, `styles`), run every task, view the results table,
  and download a `results.json` matching the container's output contract.

Each visitor picks a provider and enters **their own API key** in the UI —
the app never reads a provider key from the server environment, so there's
nothing to leak or exhaust on a shared key. The key is used only in-memory
for that request and is never logged or stored. Selecting `openai` also
reveals optional **Base URL** / **Model** fields (mirroring the container's
`OPENAI_BASE_URL`/`OPENAI_MODEL`), so you can point the demo at your own
OpenAI-compatible server (e.g. a local Lemonade instance) — in that case the
API key field can be left blank.

### Run the demo locally

```bash
uv sync --extra demo   # or: pip install -r requirements.txt
uv run python app.py   # or: python app.py, if you used pip install
```

`ffmpeg` must be on PATH. Note the `--extra demo` (or `requirements.txt`) —
`app.py` needs `gradio`/`pandas` on top of the base container dependencies,
so a plain `uv sync` / `pip install .` is not enough to run it.

Then open the local URL it prints and enter your own provider API key in
the UI — no environment variables required to start it.

### Deploy to Render (free tier)

The demo ships with `Dockerfile.demo` and `render.yaml` for a one-click
Render deploy — no credit card required on Render's free plan.

1. Push this repo to GitHub/GitLab (Render deploys from a connected repo).
2. In the [Render dashboard](https://dashboard.render.com), **New → Blueprint**
   and point it at the repo — it picks up `render.yaml` automatically
   (service: Docker runtime, `Dockerfile.demo`, free plan). Alternatively,
   **New → Web Service**, select **Docker**, and set the Dockerfile path to
   `Dockerfile.demo` manually.
3. No provider secret to configure — visitors supply their own API key in
   the UI, so the service holds no credentials.
4. Once it builds, the service's public URL — `render.yaml` names the
   service `framewise-demo`, so `https://framewise-demo.onrender.com` — is
   the demo's Application URL. The free plan spins the service down after
   ~15 minutes idle, so the first request after a gap takes 30-50s to wake up.

Demo-only guardrails (env vars, all optional): `DEMO_MAX_VIDEO_MB` (default
50), `DEMO_MAX_BATCH_TASKS` (default 10), `DEMO_MAX_REQUESTS_PER_SESSION`
(default 20) — protect the shared free-tier compute this demo runs on from a
runaway upload or a single session hogging the instance. `DEMO_MAX_PARALLEL_TASKS`
(default **1**) caps how many batch tasks run concurrently; it's kept at 1
because Render's free tier is capped at 512MB and each concurrent task holds
a downloaded clip, decoded frames, and its base64 payload in memory at once —
raise it only on a host with real headroom (e.g. when running locally).

## Caption providers

The provider is chosen at runtime via `CAPTION_PROVIDER`:

| `CAPTION_PROVIDER` | Model input | API key env var | Notes |
| --- | --- | --- | --- |
| `gemini` (default) | native video | `GEMINI_API_KEY` | uploads the clip via the Files API |
| `openai` | sampled frames | `OPENAI_API_KEY` | frames sent as images in one call |
| `anthropic` | sampled frames | `ANTHROPIC_API_KEY` | frames sent as images in one call |

Each clip is captioned in a **single call** that returns one caption per
requested style as JSON. Optional overrides: `GEMINI_MODEL` / `OPENAI_MODEL` /
`ANTHROPIC_MODEL`, `OPENAI_BASE_URL` (point the `openai` provider at any
OpenAI-compatible server — see [Run locally with Lemonade](#run-locally-with-lemonade-no-cloud-no-key)),
`FRAME_INTERVAL_SECONDS` (default 4 — one sampled frame every N seconds),
`MAX_FRAMES` (default 30 — hard cap regardless of clip length), `FRAME_LONG_SIDE`,
`REQUEST_TIMEOUT`, `MAX_RETRIES`.

**Prerequisites at run time:** network egress to the provider and a valid API
key for the selected provider. If the provider is unreachable or the key is
missing, the run fails loudly (non-zero exit) rather than emitting fabricated
captions — the `results.json` it writes is always well-formed JSON.

### Run

```bash
docker run --rm \
  -e CAPTION_PROVIDER=gemini \
  -e GEMINI_API_KEY=... \
  -v /path/to/tasks.json:/input/tasks.json:ro \
  -v /path/to/output:/output \
  <image>
```

### Run locally (no Docker, no interface)

Runs the same `main.py` entrypoint the container runs, straight on the host —
needs `ffmpeg`/`ffprobe` on PATH (used to probe clip duration and, for the
frame-based providers, sample frames):

```bash
uv sync   # or: pip install .
CAPTION_PROVIDER=gemini GEMINI_API_KEY=... \
INPUT_PATH=./sample_tasks.json OUTPUT_PATH=./results.json \
uv run python main.py   # or: python main.py, if you used pip install
```

### Run locally with an interface (Gradio demo)

Same pipeline, with a browser UI to upload a video/URL or a batch
`tasks.json` — see [Run the demo locally](#run-the-demo-locally) above.

```bash
uv sync --extra demo   # or: pip install -r requirements.txt
uv run python app.py   # or: python app.py
```

### Run locally with Lemonade (no cloud, no key)

[Lemonade](https://lemonade-server.ai/) serves local models behind an
**OpenAI-compatible** API, so the `openai` provider can target it by setting
`OPENAI_BASE_URL` — no cloud account or key required. Because that adapter is
frame-based, load a **vision-capable** model in Lemonade (e.g. a Qwen2.5-VL
variant); text-only models can't caption frames.

1. Install and start Lemonade (default port `8000`):

   ```bash
   pip install lemonade-sdk
   lemonade-server serve
   ```

2. Pull/load a vision model and note its served name:

   ```bash
   lemonade-server list          # see available / installed models
   lemonade-server pull <vision-model>
   ```

3. Point the agent at it. Running on the host (no container):

   ```bash
   CAPTION_PROVIDER=openai \
   OPENAI_BASE_URL=http://localhost:13305/api/v1 \
   OPENAI_MODEL=<vision-model> \
   INPUT_PATH=./sample_tasks.json OUTPUT_PATH=./results.json \
   python3 main.py
   ```

   From the container, reach the host's Lemonade server with host networking:

   ```bash
   docker run --rm --network=host \
     -e CAPTION_PROVIDER=openai \
     -e OPENAI_BASE_URL=http://localhost:13305/api/v1 \
     -e OPENAI_MODEL=<vision-model> \
     -v "$PWD/sample_tasks.json:/input/tasks.json:ro" \
     -v "$PWD/out:/output" \
     framewise
   ```

   (On macOS/Windows Docker Desktop use `http://host.docker.internal:8000/api/v1`
   instead of `--network=host`.)

Any other OpenAI-compatible local server (vLLM, LM Studio, Ollama) works the same
way — just change `OPENAI_BASE_URL` and `OPENAI_MODEL`.

### Optional: bake a key into the image

For environments that cannot inject environment variables, a key can be embedded
at build time (**off by default**). Prefer runtime `-e` injection; a baked key
ships inside the image.

```bash
docker build \
  --build-arg BAKE_PROVIDER_KEY_ENV=GEMINI_API_KEY \
  --build-arg BAKE_PROVIDER_KEY=... \
  -t framewise .
```

Runtime `-e` values always override a baked key.

## Docker image

Every push to `main` and every `v*` tag automatically builds and publishes the image via GitHub Actions (see `.github/workflows/docker-publish.yml`) to GitHub Container Registry:

```
ghcr.io/akay7/amd-act2-track2-video_captioning_agent
```

(Docker/OCI image names must be lowercase, so the repository's `Akay7/AMD-ACT2-track2-video_captioning_agent` path is lowercased by the workflow.) Available tags: `latest` (default branch), the branch name, `sha-<commit>`, and semver tags (`X.Y.Z`, `X.Y`) for `v*` releases.

*The image path above is derived automatically from the GitHub repository
name and is accurate today. Once the repository is renamed to `FrameWise`,
the same workflow publishes to `ghcr.io/akay7/framewise` with no code
change — this doc will be updated to match at that point.*

### Pull and run

```bash
docker pull ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest

docker run --rm \
  -e CAPTION_PROVIDER=gemini \
  -e GEMINI_API_KEY=... \
  -v /path/to/tasks.json:/input/tasks.json:ro \
  -v /path/to/output:/output \
  ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest
```

### Build locally

```bash
docker build -t framewise .
```

## Testing

All test code and fixtures live in `tests/`, which is excluded from the Docker
build context via `.dockerignore` — tests never enter the image or count against
the 10 GB compressed cap.

The tests enforce the **output contract**: `/output/results.json` must be a JSON
array with exactly one result per input task (matched by `task_id`), and each
result's `captions` object must contain a **non-empty string for every requested
style**. The contract is defined once in `validation.py`, which the tests and the
runtime self-check in `main.py` both use.

### Fast tests (no Docker, no network, no keys)

The contract test validates good/bad `results.json` fixtures; the provider test
stubs the SDKs to check provider selection, the missing-key and unknown-provider
errors, and style-subset parsing. Both run anywhere:

```bash
python tests/test_contract.py
python tests/test_providers.py
# or, if pytest is installed:
python -m pytest tests/test_contract.py tests/test_providers.py
```

### End-to-end container test (Docker + network + API key)

Runs the built image against a fixture task and asserts the container exits 0 and
writes a `results.json` that satisfies the contract. It is **skipped unless
`RUN_E2E=1`**, and needs Docker, network egress, and a valid provider API key:

```bash
RUN_E2E=1 \
  IMAGE=ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest \
  CAPTION_PROVIDER=gemini GEMINI_API_KEY=... \
  python tests/run_e2e.py
```

Environment overrides: `IMAGE` (image tag), `E2E_TASKS` (tasks fixture path),
`CAPTION_PROVIDER` and its `*_API_KEY`, `DOCKER_RUN_FLAGS` (extra `docker run`
flags), `E2E_TIMEOUT` (max run seconds).
