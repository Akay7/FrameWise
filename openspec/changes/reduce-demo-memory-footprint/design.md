## Context

The demo app (`app.py`) added parallel batch execution
(`ThreadPoolExecutor`, default 4 workers) to fix a UX complaint — the batch
tab looked frozen because it only yielded a status update once, at the
start, and multi-clip runs on a slow free-tier instance could take minutes.
Concurrency fixed the perceived-hang problem but traded it for a real one:
running 4 full per-task pipelines (download → `ffmpeg` frame extraction →
base64 encode → provider API call) at once is memory-expensive, and
Render's free plan caps the whole process at 512MB. This was confirmed live:
the batch tab, `openai`/`anthropic` provider, real 4K sample clips → OOM
kill.

## Goals / Non-Goals

**Goals:**
- Bring the demo's default memory footprint safely under a 512MB budget on
  the free tier, without giving up the progress-feedback fix that motivated
  parallelism in the first place.
- Reduce frame-based providers' per-clip cost in general (not just for the
  demo) — a fixed 12-frame sample was already more than most short clips
  need.
- Keep every default overridable via env var for hosts with real headroom.

**Non-Goals:**
- Not attempting fine-grained memory accounting or a hard per-request
  memory limit — the fix is reducing worst-case concurrent memory use via
  simpler, coarser levers (concurrency, video size, frame count).
- Not changing the native-video path (Gemini) — it doesn't decode frames
  locally, so it wasn't implicated in the OOM.

## Decisions

- **`MAX_PARALLEL_TASKS` default 4 → 1.** Sequential-by-default is the only
  change that's unconditionally safe regardless of clip size/count — it
  restores the exact concurrency profile the batch tab had before
  parallelism was added (which never OOM'd), while keeping the per-task
  incremental-yield progress feedback (the part that actually fixed the
  "looks frozen" complaint; concurrency was a bonus speedup, not the fix).
  Alternative considered: lower to 2 as a compromise — rejected because the
  confirmed-crashing case (4K clips, frame-based provider) leaves too
  little margin at 2 concurrent full pipelines on a 512MB box; users who
  want the speedup on a bigger host can raise it via
  `DEMO_MAX_PARALLEL_TASKS`.
- **`MAX_VIDEO_MB` default 200 → 50.** 200MB was sized without the 512MB
  ceiling in mind. 50MB still comfortably covers the hackathon sample clips
  (8-20MB) and typical short demo uploads.
- **Frame sampling: fixed count → fixed rate + cap.** `FRAME_INTERVAL_SECONDS`
  (default 4) replaces `NUM_FRAMES` (was a flat 12 regardless of duration).
  `MAX_FRAMES` (default 30) bounds the other direction — a long clip can't
  balloon frame count/memory unboundedly. Net effect: short clips (like the
  ~6s hackathon samples) now sample 1-2 frames instead of 12, a large
  reduction in per-task memory/payload for exactly the case that OOM'd.
  This changes `main.py`/the container's frame-based behavior too, not just
  the demo — accepted, since the old fixed-12 behavior wasn't a documented
  contract requirement, just an implementation default, and rate-based
  sampling is a reasonable default improvement either way.
- **Single-pass extraction via `ffmpeg`'s `fps` filter**, replacing one
  `ffmpeg` subprocess per frame. Independent of the memory fix, but found
  while touching this code — cheaper (one process spawn instead of up to
  12) and simpler.
- **`GRADIO_ANALYTICS_ENABLED=False` in `Dockerfile.demo`.** Found while
  debugging locally (a slow/blocked path to Gradio's telemetry endpoint
  made local script exits hang) — doesn't affect a long-running web service
  the same way, but removing an unneeded outbound call is a reasonable
  default regardless.

## Risks / Trade-offs

- [Sequential batch execution is slower wall-clock than the 4-way parallel
  version for multi-task batches] → Accepted: reliability over speed for
  the default free-tier deployment; `DEMO_MAX_PARALLEL_TASKS` is still
  there for anyone running on a host with real memory headroom.
- [Fewer sampled frames could reduce caption quality/detail for
  fast-changing or long clips] → `FRAME_INTERVAL_SECONDS`/`MAX_FRAMES` are
  both env-var-overridable; the 4s/30-frame defaults are a starting point,
  not a hard claim about optimal captioning quality.
- [Changing frame sampling changes the container's grading-time behavior
  for `openai`/`anthropic`, not just the demo] → Flagged explicitly in the
  proposal; `NUM_FRAMES` was never a documented contract requirement in
  `specs/external-caption-provider/spec.md`, so this isn't a breaking
  change to any stated requirement, just a default tuning.

## Migration Plan

1. Update `media.py` (rate-based `extract_frames`), `providers.py` (call
   site), `app.py` (parallelism/video-size defaults), `Dockerfile.demo`
   (analytics env var), `README.md` (env var docs).
2. Verify: unit-check `extract_frames` against a real sample clip (frame
   count matches `duration / interval`, capped correctly); full test suite
   (`test_contract.py`, `test_providers.py`) still passes.
3. Push to the branch Render deploys from; the free-tier service picks up
   the new defaults on its next build.
4. No rollback complexity — every changed default is env-var-overridable
   without a code change if it turns out too conservative.

## Open Questions

- None outstanding.
