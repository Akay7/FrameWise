## 1. Provider abstraction

- [x] 1.1 Add `providers.py` with a `CaptionProvider` protocol exposing `caption_clip(clip_path, duration, styles) -> dict[str, str]`.
- [x] 1.2 Add `get_provider(name)` factory that maps `CAPTION_PROVIDER` values (`gemini`, `openai`, `anthropic`) to adapters, raises a clear error on unknown names, and applies the documented default when unset.
- [x] 1.3 Add a shared credential loader that reads `<PROVIDER>_API_KEY` and exits with the exact missing var name when absent/empty.
- [x] 1.4 Move the existing ffmpeg frame-sampling helper into a shared location reusable by frame-based adapters.

## 2. Provider adapters

- [x] 2.1 Implement the Gemini adapter: upload the clip via the Files API, submit as native video, request strict JSON keyed by style, one call per clip.
- [x] 2.2 Implement the OpenAI adapter: sample frames, send as images in one call, request strict JSON keyed by style.
- [x] 2.3 Implement the Anthropic adapter: sample frames, send as images in one call, request strict JSON keyed by style.
- [x] 2.4 Reuse the existing prompt/style-guide and `_parse_captions` logic so all adapters return `{style: caption}` for only the requested styles.
- [x] 2.5 Add bounded retries with backoff and a per-request timeout under 30s; on unrecoverable failure raise rather than fabricate captions.

## 3. Pipeline integration

- [x] 3.1 Rewrite `main.py` to load the provider and validate the key at startup (before processing any task).
- [x] 3.2 Replace local-inference `caption_clip` calls with the provider client, keeping per-task download/duration probing.
- [x] 3.3 On provider failure, write whatever valid results exist, run the `validation.py` self-check, and exit non-zero.
- [x] 3.4 Remove all local-model code paths (model load, torch/transformers usage, CAPTION_MODE two-pass local logic).

## 4. Dependencies and image

- [x] 4.1 Update `pyproject.toml`: remove `torch`, `torchvision`, `transformers`, `qwen-vl-utils`, `accelerate`, `sentencepiece`; add the provider SDK(s) (`google-genai`, `openai`, `anthropic`).
- [x] 4.2 Rewrite the Dockerfile on `python:3.11-slim` + `ffmpeg`; remove the ROCm wheel index and the model-download step.
- [x] 4.3 Add an optional, off-by-default `BAKE_KEY` build arg that embeds a key into the image for judges that cannot inject env vars.
- [x] 4.4 Verify the image builds and is far under the 10 GB compressed cap.

## 5. Tests and docs

- [x] 5.1 Update `tests/run_e2e.py` to pass the provider key through `docker run` and drop the GPU flags.
- [x] 5.2 Add a fast, network-free adapter unit test (mock the SDK) verifying provider selection, missing-key error, unknown-provider error, and style-subset parsing.
- [x] 5.3 Confirm `tests/test_contract.py` still passes unchanged.
- [x] 5.4 Update `README.md`: provider selection, required env vars, network prerequisite, optional build-time key, and the removal of the GPU requirement.

## 6. Verify

- [x] 6.1 Run the contract and adapter unit tests; confirm pass with no network.
- [x] 6.2 With a real key, run one clip end-to-end through the default provider and confirm a valid `results.json`. Ran directly against the built `video-caption:latest` image (bypassing `run_e2e.py`'s bind mount, which needs a podman `:Z` SELinux label this sandbox's rootless podman requires but the script doesn't add) via `openai` provider pointed at a local Lemonade server (`OPENAI_BASE_URL`, `Qwen3-VL-8B-Instruct-GGUF`, no real cloud key needed). Container exited 0, wrote a `results.json` with grounded, distinct captions for all 4 styles, self-check passed, and `validation.load_and_validate` reported zero errors.
- [x] 6.3 Run `openspec validate use-external-caption-service --strict` and fix any issues.
