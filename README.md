# Track 2 — Video Captioning Agent

Reads `/input/tasks.json`, generates a caption per requested style for every clip using a single local video-native VLM (Qwen2.5-VL, run on ROCm), and writes `/output/results.json`.

## Docker image

Every push to `main` and every `v*` tag automatically builds and publishes the image via GitHub Actions (see `.github/workflows/docker-publish.yml`) to GitHub Container Registry:

```
ghcr.io/akay7/amd-act2-track2-video_captioning_agent
```

(Docker/OCI image names must be lowercase, so the repository's `Akay7/AMD-ACT2-track2-video_captioning_agent` path is lowercased by the workflow.) Available tags: `latest` (default branch), the branch name, `sha-<commit>`, and semver tags (`X.Y.Z`, `X.Y`) for `v*` releases.

### Pull and run

```bash
docker pull ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest

docker run --rm \
  -v /path/to/tasks.json:/input/tasks.json:ro \
  -v /path/to/output:/output \
  ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest
```

### Build locally

```bash
docker build -t video-captioning-agent .
```

Override the ROCm wheel channel to match your host's ROCm version if needed:

```bash
docker build --build-arg ROCM_INDEX=https://download.pytorch.org/whl/rocm6.3 -t video-captioning-agent .
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

### Contract test (fast, no GPU/Docker)

Validates good and bad `results.json` fixtures against the contract. Runs anywhere:

```bash
python tests/test_contract.py
# or, if pytest is installed:
python -m pytest tests/test_contract.py
```

### End-to-end container test (Docker + AMD GPU)

Runs the built image against a fixture task and asserts the container exits 0 and
writes a `results.json` that satisfies the contract. It is **skipped unless
`RUN_E2E=1`**, and needs Docker, an AMD ROCm GPU, and network access to download
the fixture clip:

```bash
RUN_E2E=1 IMAGE=ghcr.io/akay7/amd-act2-track2-video_captioning_agent:latest \
  python tests/run_e2e.py
```

Environment overrides: `IMAGE` (image tag), `E2E_TASKS` (tasks fixture path),
`DOCKER_GPU_FLAGS` (GPU `docker run` flags), `E2E_TIMEOUT` (max run seconds).
