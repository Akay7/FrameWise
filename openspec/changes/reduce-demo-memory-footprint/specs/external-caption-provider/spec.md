## MODIFIED Requirements

### Requirement: Per-clip multi-style caption generation

For each clip, the system SHALL request captions for all requested styles from
the provider, preferring native video input where the provider supports it and
otherwise sending sampled frames from the clip. The provider response SHALL be
parsed into a mapping of style name to a non-empty English caption string.
When sending sampled frames, the system SHALL sample at a fixed rate (one
frame per `FRAME_INTERVAL_SECONDS`, default 4 seconds) rather than a fixed
frame count, and SHALL cap the total sampled frames at `MAX_FRAMES` (default
30) regardless of clip duration.

#### Scenario: Native-video provider

- **WHEN** the active provider supports native video and a clip with four requested styles is processed
- **THEN** the clip is submitted as video and the response yields one caption per requested style

#### Scenario: Frame-based provider

- **WHEN** the active provider does not support native video
- **THEN** the system samples frames from the clip and submits them as images, yielding one caption per requested style

#### Scenario: Only requested styles returned

- **WHEN** a task requests a subset of the four styles
- **THEN** the result contains captions only for the requested styles

#### Scenario: Short clip samples fewer frames

- **WHEN** a frame-based provider processes a clip shorter than
  `FRAME_INTERVAL_SECONDS × MAX_FRAMES` (e.g. a 6-second clip at the
  4-second default interval)
- **THEN** the number of sampled frames is proportional to the clip's
  duration (`duration / FRAME_INTERVAL_SECONDS`, rounded up), not a fixed
  count

#### Scenario: Long clip is capped

- **WHEN** a frame-based provider processes a clip long enough that
  rate-based sampling would exceed `MAX_FRAMES`
- **THEN** exactly `MAX_FRAMES` frames are sampled, spread across the clip
  at the configured rate up to that cap
