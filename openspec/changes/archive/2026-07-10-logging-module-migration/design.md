## Context

`main.py`, `media.py`, and `providers.py` currently write progress/error
output with bare `print()`. This predates concurrent task execution
(`MAX_PARALLEL_TASKS`, default 10 in the container); with multiple tasks
in flight, unlabelled/untimestamped `print` output from different threads
interleaves and is hard to attribute. Some stage-level prints were already
added ad hoc this session (probe duration, frame extraction count, base64
encoding count, Gemini upload/send/receive) directly as `print()` calls —
this change converts those plus the rest of the pipeline's output to
`logging`, and fills in the one remaining gap (OpenAI/Anthropic adapters
don't yet log their send/receive stage).

## Goals / Non-Goals

**Goals:**
- One consistent way to emit runtime output across the three pipeline
  modules, using the stdlib `logging` module only.
- Timestamps + level + module name on every line, so concurrent-task output
  is attributable and greppable.
- Verbosity controllable at runtime via `LOG_LEVEL` (no code change needed
  to quiet or raise output).
- Full stage visibility from "clip downloaded" to "caption received":
  duration probe, frame extraction, base64 encoding, model send/receive —
  for every provider (Gemini, OpenAI, Anthropic), not just Gemini.

**Non-Goals:**
- No change to `results.json` shape, provider selection logic, retry
  policy, or the `MAX_PARALLEL_TASKS` concurrency model.
- No structured/JSON logging, no log shipping/aggregation integration —
  plain text to stdout is sufficient for a container whose logs are read
  via `docker logs`/`podman logs`.
- `app.py` (the Gradio demo) is out of scope: its single `print()` for
  batch-task errors is a separate, demo-only code path and isn't part of
  the container's stdout contract.

## Decisions

- **Per-module logger via `logging.getLogger(__name__)`.** Standard
  pattern; keeps module name in every line for free via the format string,
  which directly helps distinguish `media` (download/extract) output from
  `providers` (model call) output during concurrent runs.
- **Configure once, in `main.py`, via `logging.basicConfig(...)` at import
  time (module level, not inside `main()`).** `main.py` is the container
  entrypoint, so this runs before any task executes. `app.py` also imports
  from `main`, so it inherits the same configuration for free (and
  `basicConfig` is a no-op if a handler is already configured, so this is
  safe regardless of import order).
- **Level from `LOG_LEVEL` env var, default `INFO`.** Matches the existing
  convention in this codebase of runtime-tunable behavior via env vars
  (`MAX_PARALLEL_TASKS`, `FRAME_INTERVAL_SECONDS`, etc.) rather than a
  code change.
- **Format: `%(asctime)s %(levelname)s %(name)s: %(message)s`.** Timestamp
  first (chronological reading), level for filtering, module name for
  attribution under concurrency.
- **Lazy `%`-style logger args (`logger.info("x=%s", x)`) instead of
  f-strings.** Avoids formatting cost when a level is disabled; idiomatic
  for stdlib `logging`.
- **`logger.exception(...)` replaces `traceback.print_exc()` + a separate
  error print**, since `logger.exception` already captures the traceback
  at ERROR level in one call.
- **Retain the existing message wording** (e.g. "Downloading %s",
  "Task %s done in %.1fs") — only the emission mechanism changes, not the
  content, to keep this a pure refactor with no behavior change beyond
  formatting/timestamps.

## Risks / Trade-offs

- [Risk] `logging.basicConfig` only takes effect on its first call in a
  process; if some other import configures logging first with a
  different format, this module's format would silently not apply. →
  Mitigation: `main.py` is the entrypoint and is imported first in both
  the container path and (transitively, before any Gradio setup) the demo
  path; no other module in this repo calls `basicConfig`.
- [Risk] Concurrent tasks (`MAX_PARALLEL_TASKS`) still interleave log
  lines from different tasks, since no per-task correlation ID is added. →
  Mitigation: out of scope for this change (would require threading a
  task_id through `media.py`/`providers.py` call signatures); timestamps
  + module name are enough to manually disentangle output for now, and
  this can be a follow-up.

## Migration Plan

Pure refactor, single PR: convert `print` → `logger.*` in the three files,
add the missing OpenAI/Anthropic stage logs, verify via the existing test
suite (`tests/test_contract.py`, `tests/test_providers.py`) plus a manual
container run to eyeball output. No rollback concerns — reverting the
commit restores prior behavior exactly (log formatting only).
