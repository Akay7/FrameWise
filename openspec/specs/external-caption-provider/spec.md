# external-caption-provider

## Purpose

TBD

## Requirements

### Requirement: Runtime provider selection

The system SHALL select a caption provider at runtime from a `CAPTION_PROVIDER`
environment variable, supporting at minimum `gemini`, `openai`, and `anthropic`.
When `CAPTION_PROVIDER` is unset, the system SHALL default to a documented
provider. When it names an unsupported provider, the system SHALL fail with a
clear error before processing any task.

#### Scenario: Explicit provider selected

- **WHEN** `CAPTION_PROVIDER=openai` is set and a valid key is present
- **THEN** the system routes all caption requests through the OpenAI adapter

#### Scenario: Default provider

- **WHEN** `CAPTION_PROVIDER` is unset
- **THEN** the system uses the documented default provider

#### Scenario: Unknown provider rejected

- **WHEN** `CAPTION_PROVIDER=doesnotexist` is set
- **THEN** the system exits with an error naming the unsupported provider and lists the supported ones

### Requirement: Credential loading from environment

The system SHALL read the active provider's API key from an environment variable
(e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) at runtime, and
SHALL NOT bake any key into the image by default. A missing key for the selected
provider SHALL cause a clear startup error rather than empty captions.

#### Scenario: Key present

- **WHEN** the selected provider's key env var is set to a valid key
- **THEN** the adapter authenticates and processes tasks

#### Scenario: Key missing

- **WHEN** the selected provider's key env var is unset or empty
- **THEN** the system exits with an error identifying which env var is required

### Requirement: Per-clip multi-style caption generation

For each clip, the system SHALL request captions for all requested styles from
the provider, preferring native video input where the provider supports it and
otherwise sending sampled frames from the clip. The provider response SHALL be
parsed into a mapping of style name to a non-empty English caption string.

#### Scenario: Native-video provider

- **WHEN** the active provider supports native video and a clip with four requested styles is processed
- **THEN** the clip is submitted as video and the response yields one caption per requested style

#### Scenario: Frame-based provider

- **WHEN** the active provider does not support native video
- **THEN** the system samples frames from the clip and submits them as images, yielding one caption per requested style

#### Scenario: Only requested styles returned

- **WHEN** a task requests a subset of the four styles
- **THEN** the result contains captions only for the requested styles

### Requirement: Fail-loud on provider failure

The system SHALL NOT silently substitute placeholder or cached captions when the
provider call fails. On an unrecoverable provider error (network failure, auth
failure, timeout after retries), the system SHALL surface the error. Whatever
results are written SHALL still pass the output-contract validator for JSON
shape, so a partial run never produces malformed JSON.

#### Scenario: Provider unreachable

- **WHEN** the provider endpoint is unreachable and retries are exhausted
- **THEN** the system logs the failure and exits non-zero rather than emitting fabricated captions

#### Scenario: Output stays well-formed

- **WHEN** the run writes `results.json` for any completed tasks
- **THEN** the file is a valid JSON array conforming to the output contract

### Requirement: Optional build-time key embedding

The system SHALL provide a documented, opt-in mechanism (e.g. a Docker build
argument) to embed an API key into the image for environments where the judge
cannot inject environment variables. This path SHALL be off by default.

#### Scenario: Build-arg key embedding

- **WHEN** the image is built with the documented key build argument supplied
- **THEN** the resulting image runs without an externally injected key

#### Scenario: Default build carries no key

- **WHEN** the image is built without the key build argument
- **THEN** the image contains no API key and requires one via environment at runtime
