## Why

The caption pipeline (`main.py`, `media.py`, `providers.py`) uses ad-hoc
`print()` calls for all runtime output. There's no severity distinction (info
vs. warning vs. error all look the same), no way to quiet/raise verbosity
without editing code, and — since tasks now run concurrently
(`MAX_PARALLEL_TASKS`) — no timestamps to help untangle interleaved output
from multiple in-flight tasks. Separately, the pipeline is a black box between
"finished downloading the clip" and "got a caption back": there's no visibility
into duration probing, frame extraction, base64 encoding, or the actual
request/response around the model call, which makes slow or hung runs (e.g.
against a local LLM) hard to diagnose.

## What Changes

- Replace all `print()` calls in `main.py`, `media.py`, and `providers.py`
  with calls to the standard `logging` module (`logging.getLogger(__name__)`
  per module).
- Configure logging once, at `main.py` import time, with a timestamp +
  level + module + message format; level controlled by a `LOG_LEVEL`
  env var (default `INFO`).
- Add pipeline-stage log lines currently missing between "clip downloaded"
  and "sent to the model": probed duration, frame extraction start + frame
  count, base64 encoding count, and a send/receive pair around each
  provider's actual model call (Gemini upload+generate; OpenAI/Anthropic
  frame-based chat call).
- Route retry warnings and task failures through `logger.warning` /
  `logger.error` (with `logger.exception` for tracebacks) instead of
  `print` + `traceback.print_exc()`.
- No change to `results.json` output, provider behavior, or the
  `MAX_PARALLEL_TASKS` concurrency model — this is stdout/observability
  only.

## Capabilities

### New Capabilities

- `pipeline-observability`: structured logging (module, level, timestamp)
  and stage-level progress visibility across the download → extract →
  encode → model-call pipeline, configurable via `LOG_LEVEL`.

### Modified Capabilities

(none — no existing spec covers current print-based output)

## Impact

- `main.py`: add logging config + `logger`, convert task lifecycle prints
  (task start/done, duration probe, self-check, final summary) to logger
  calls.
- `media.py`: convert download/copy/frame-extraction prints to logger calls.
- `providers.py`: convert retry-warning and provider-adapter prints to
  logger calls; add matching send/receive stage logs to the OpenAI and
  Anthropic adapters (Gemini adapter already has these from prior work
  this session).
- `app.py`: unaffected in behavior; its one `print()` for batch-task errors
  is out of scope (separate demo-only code path), left as-is.
- No new dependencies (`logging` is stdlib); no change to `pyproject.toml`,
  `Dockerfile`, or output contract.
