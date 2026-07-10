## ADDED Requirements

### Requirement: Structured logging via the standard library

The system SHALL emit all pipeline runtime output (`main.py`, `media.py`,
`providers.py`) through the standard `logging` module rather than `print`,
using a per-module logger obtained via `logging.getLogger(__name__)`. Each
log line SHALL include a timestamp, severity level, and the emitting
module's name.

#### Scenario: Log line format

- **WHEN** any pipeline module emits a log message
- **THEN** the resulting line includes a timestamp, a level name (e.g.
  `INFO`, `WARNING`, `ERROR`), the module name, and the message text

#### Scenario: Errors captured with traceback

- **WHEN** a task fails with an exception during `run_tasks`
- **THEN** the system logs the failure at `ERROR` level including the
  exception traceback, via the logger rather than `print` +
  `traceback.print_exc()`

### Requirement: Runtime-configurable log level

The system SHALL read the desired log verbosity from a `LOG_LEVEL`
environment variable at startup, defaulting to `INFO` when unset, and
apply it to all pipeline loggers without requiring a code change.

#### Scenario: Default level

- **WHEN** `LOG_LEVEL` is not set
- **THEN** the system logs at `INFO` level and above

#### Scenario: Explicit level override

- **WHEN** `LOG_LEVEL=DEBUG` (or another valid level name) is set
- **THEN** the system logs at that level and above instead of the default

### Requirement: Full pipeline stage visibility

For every task, the system SHALL log a distinguishable stage message at
each of the following points, for every caption provider (Gemini, OpenAI,
Anthropic): after the clip download completes, after duration probing,
before and after frame extraction (with the resulting frame count), after
base64-encoding frames (frame-based providers only), and immediately
before sending to and immediately after receiving from the model.

#### Scenario: Frame-based provider (OpenAI/Anthropic) stage logs

- **WHEN** a task is captioned via the `openai` or `anthropic` provider
- **THEN** the log includes, in order, the probed duration, frame
  extraction start and resulting frame count, the base64 encoding count,
  a "sending to <provider>" message, and a "received response" message

#### Scenario: Native-video provider (Gemini) stage logs

- **WHEN** a task is captioned via the `gemini` provider
- **THEN** the log includes the probed duration, an upload-start message,
  a "sending to Gemini" message, and a "received response" message
  (frame extraction/encoding stages are skipped, since Gemini consumes
  the native video file directly)
