## Why

The live demo (`framewise-demo.onrender.com`, Render's free 512MB-RAM tier)
was OOM-killed ("Ran out of memory (used over 512MB)") while running the
batch tab with a frame-based provider (`openai`/`anthropic`). Root cause:
the batch tab's parallel execution (added to fix a separate "looks frozen"
UX issue) ran up to 4 tasks concurrently by default, and each concurrent
task downloads its own clip, runs its own `ffmpeg` frame extraction, and
holds its own base64-encoded frame set in memory at once — on a 512MB box
with real 4K sample clips, that's enough to exceed the limit. Frame
sampling itself was also more generous than it needed to be: a fixed 12
frames per clip regardless of duration, even for the ~6-second hackathon
sample clips.

## What Changes

- **Batch tab defaults to sequential execution.** `DEMO_MAX_PARALLEL_TASKS`
  default drops from 4 to 1 — safe on the smallest free-tier hosts by
  default; raise it via env var only on a host with real memory headroom.
- **Lower the default per-video size cap.** `DEMO_MAX_VIDEO_MB` drops from
  200 to 50 — 200MB was never a realistic budget on a 512MB container once
  processing overhead is counted.
- **Frame sampling switches from a fixed count to a fixed rate.** Instead
  of always extracting 12 frames per clip, the frame-based providers
  (`openai`/`anthropic`) now sample one frame every `FRAME_INTERVAL_SECONDS`
  (default 4s), capped at `MAX_FRAMES` (default 30) regardless of clip
  length. A short clip now costs proportionally less memory/payload; a very
  long clip is protected from unbounded frame growth by the cap.
- **Frame extraction runs as a single `ffmpeg` pass** (via the `fps` filter)
  instead of one `ffmpeg` subprocess per frame — cheaper and simpler,
  independent of the memory fix.
- Disable Gradio's analytics/telemetry call
  (`GRADIO_ANALYTICS_ENABLED=False`) in `Dockerfile.demo` — removes an
  unnecessary outbound network dependency at process start/exit.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `external-caption-provider`: "Per-clip multi-style caption generation"
  now specifies rate-based, capped frame sampling for frame-based providers
  instead of an unbounded fixed count.
- `demo-web-app`: adds a requirement that batch execution stays within the
  memory budget of a small free-tier host by default (sequential unless
  explicitly raised, and a conservative per-video size cap).

## Impact

- **Code**: `media.py` (`extract_frames` rewritten for rate-based, single-pass
  sampling), `providers.py` (`_b64_frames` call site simplified), `app.py`
  (`MAX_PARALLEL_TASKS`/`MAX_VIDEO_MB` defaults), `Dockerfile.demo`
  (`GRADIO_ANALYTICS_ENABLED`).
- **Docs**: `README.md`'s env var list updated
  (`FRAME_INTERVAL_SECONDS`/`MAX_FRAMES` replace `NUM_FRAMES`).
- **Behavior change for `main.py`/the container too**: frame-based providers
  now sample by rate/cap instead of a fixed count of 12 — this is a
  behavior change for the graded container's `openai`/`anthropic` paths,
  not just the demo (Gemini's native-video path is unaffected).
