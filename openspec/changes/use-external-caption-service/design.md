## Context

The current agent bakes Qwen2.5-VL-3B and a ROCm torch stack into the image and
runs on-device inference. That assumes the judge VM exposes a compatible AMD GPU
— an assumption we cannot verify. The hackathon rules allow calling external
services, so we can trade the hardware bet for a network bet: a hosted vision
model that runs anywhere, produces stronger captions, and lets the image be
tiny and start in seconds. The output contract (`validation.py`) and the
tasks/results JSON shape are unchanged.

Decided constraints from the user:
- **Multi-provider**, selected by env var (Gemini, OpenAI, Anthropic).
- **Pure external** — no local model fallback.
- **Env-var credentials**, with an opt-in build-time embedding path.

## Goals / Non-Goals

**Goals:**
- Remove all GPU/ROCm/torch dependencies and the baked model weights.
- One clean adapter interface with three interchangeable implementations.
- Single call per clip returning all requested styles as JSON.
- Prefer native video input (Gemini) and fall back to sampled frames otherwise.
- Fail loudly and early on missing key / unknown provider; never fabricate
  captions; always keep `results.json` well-formed.
- Keep the existing frame-extraction (ffmpeg) code, reused for frame-based
  providers.

**Non-Goals:**
- No local-model fallback (explicitly dropped).
- No multi-provider ensembling or cross-checking in this change.
- No change to the output contract or the tasks/results schema.
- No caching of provider responses (rules forbid answer caching).

## Decisions

**Adapter interface.** A small `CaptionProvider` protocol with one method,
`caption_clip(clip_path, duration, styles) -> dict[str, str]`. A factory
`get_provider(name)` returns the configured adapter. `main.py` depends only on
the protocol, so swapping providers is an env change, not a code change.
*Alternative considered:* inline `if provider == ...` branches in `main.py` —
rejected as harder to test and extend.

**Provider capabilities.**
- *Gemini* (`google-genai`): upload the clip via the Files API and pass it as
  native video in one request — best temporal grounding, one call per clip.
- *OpenAI* (`openai`) and *Anthropic* (`anthropic`): no native video, so reuse
  the existing ffmpeg frame sampler (interior-sampled, downscaled) and send N
  frames as images in one request.
Each adapter sends the same style-guide prompt and requests strict JSON keyed by
style, parsed by the existing `_parse_captions` logic.

**Credentials.** Read `<PROVIDER>_API_KEY` at startup. Missing key → exit
non-zero with the exact var name. Default no key in image; an optional
`--build-arg BAKE_KEY=...` writes it to an env in the image for judges that
cannot pass env vars (documented as a fallback, discouraged).

**Failure policy.** Per-clip: bounded retries with backoff on transient errors.
If a clip ultimately fails, the run exits non-zero after writing whatever valid
results exist; we never write placeholder captions. The `validation.py`
self-check still runs so the emitted JSON is always well-formed.

**Dependencies.** Drop `torch`, `torchvision`, `transformers`, `qwen-vl-utils`,
`accelerate`, `sentencepiece`. Add only the SDK(s) needed; keep `requests` and
`Pillow` for download/frame handling. Base image becomes slim `python:3.11-slim`
+ `ffmpeg`.

## Risks / Trade-offs

- **No network / no key at judge time → total failure.** This is the accepted
  cost of "pure external." → Mitigate by documenting the network+key
  prerequisite prominently, verifying against the hackathon rules, and offering
  the build-time key embedding escape hatch. (Open question below.)
- **Per-request latency and the <30s / 10-min budgets.** External round-trips
  plus (for Gemini) a file upload add latency. → Prefer the fastest model tier,
  one call per clip, bounded retries, and a hard per-request timeout below 30s.
- **Provider API/SDK drift.** Three SDKs to track. → Keep adapters thin and
  behind the protocol; only one provider is exercised per run.
- **Cost / rate limits during judging.** ~12 clips is small, but rate limits
  could bite. → Backoff + single-call-per-clip keeps request count minimal.
- **Vendor TOS on baked keys.** Embedding a key in a shared image risks leakage.
  → Off by default; documented as last resort only.

## Migration Plan

1. Add `providers.py` (protocol + factory + three adapters) reusing the existing
   ffmpeg frame sampler.
2. Rewrite `main.py` to load the provider, validate the key, and call
   `caption_clip` per task; keep the `validation.py` self-check.
3. Slim the Dockerfile (python-slim + ffmpeg), remove ROCm/model-download steps,
   add optional `BAKE_KEY` build arg.
4. Update `pyproject.toml` deps and `README.md` (provider/credentials/network).
5. Update `tests/run_e2e.py` to pass the key and drop GPU flags.
6. Rollback: the local-model implementation remains in git history; revert the
   commit to restore it if external access proves unavailable.

## Open Questions

- **How does the judge inject secrets and is network egress allowed?** Confirm
  against the hackathon rules. If env vars are not supported, the build-time key
  path becomes mandatory rather than optional.
- **Which default provider?** Leaning Gemini for native video; confirm the
  user has a key for the intended default.
