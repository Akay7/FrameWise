## ADDED Requirements

### Requirement: Resource-bounded batch execution on constrained hosts
The batch tasks-file tab SHALL default to a concurrency and per-video size
that fits within a small free-tier host's memory budget (512MB), while
remaining configurable via environment variables for hosts with more
headroom.

#### Scenario: Sequential by default
- **WHEN** the app starts without `DEMO_MAX_PARALLEL_TASKS` set
- **THEN** batch tasks are processed one at a time (not concurrently)

#### Scenario: Concurrency raised explicitly
- **WHEN** `DEMO_MAX_PARALLEL_TASKS` is set above 1
- **THEN** the batch tab runs up to that many tasks concurrently

#### Scenario: Conservative default video size cap
- **WHEN** the app starts without `DEMO_MAX_VIDEO_MB` set
- **THEN** uploaded videos over 50MB are rejected with a validation message,
  rather than accepted and risking exhausting the host's memory during
  processing
