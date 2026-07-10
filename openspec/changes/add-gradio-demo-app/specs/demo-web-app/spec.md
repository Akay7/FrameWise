## ADDED Requirements

### Requirement: Single-video captioning tab
The demo app SHALL provide a UI tab where a user submits one video (by
file upload or by URL) and one or more caption styles, and receives the
generated caption for each selected style from the same provider pipeline
the container uses.

#### Scenario: Caption an uploaded video
- **WHEN** a user uploads a video file and selects one or more styles, then
  submits
- **THEN** the app runs the clip through the configured caption provider
  and displays a non-empty caption for every selected style

#### Scenario: Caption a video by URL
- **WHEN** a user pastes a video URL instead of uploading a file, selects
  styles, and submits
- **THEN** the app downloads the clip from the URL and displays a caption
  for every selected style, using the same code path as the upload case

#### Scenario: No styles selected
- **WHEN** a user submits without selecting any style
- **THEN** the app rejects the submission with a validation message and
  does not call the caption provider

### Requirement: Batch tasks-file captioning tab
The demo app SHALL provide a UI tab where a user uploads a `tasks.json`
file in the same shape as `sample_tasks.json` (a JSON array of objects
with `task_id`, `video_url`, and `styles`), and receives one result per
task.

#### Scenario: Run a valid batch file
- **WHEN** a user uploads a well-formed `tasks.json` with one or more tasks
- **THEN** the app runs every task through the caption pipeline and
  displays a results table with one row per `task_id`, each row showing
  every requested style's caption

#### Scenario: Download batch results
- **WHEN** a batch run completes
- **THEN** the app offers the results as a downloadable JSON file matching
  the container's output contract (one entry per task, `captions` keyed by
  style, non-empty string per requested style)

#### Scenario: Malformed batch file
- **WHEN** a user uploads a file that is not valid JSON, or whose entries
  are missing `video_url`
- **THEN** the app shows an error identifying the problem and does not
  attempt to call the caption provider for that file

### Requirement: Shared provider configuration
The demo app SHALL select and configure the caption provider using the
same `CAPTION_PROVIDER` and `<PROVIDER>_API_KEY` environment variables the
container uses, and SHALL NOT expose a UI control for entering or
overriding provider API keys.

#### Scenario: Provider selected via environment
- **WHEN** the app starts with `CAPTION_PROVIDER=gemini` and
  `GEMINI_API_KEY` set in the environment
- **THEN** both the single-video and batch tabs use the Gemini adapter for
  every request, with no per-request key input in the UI

#### Scenario: Missing provider key at startup
- **WHEN** the app starts without a valid API key for the configured
  provider
- **THEN** the app fails to start (or displays a persistent configuration
  error) rather than accepting submissions it cannot fulfill

### Requirement: Hosted, publicly reachable demo
The demo app SHALL be deployed to a hosting platform that provides a
stable public URL reachable without the visitor installing Docker or
cloning the repository.

#### Scenario: Judge opens the demo URL
- **WHEN** a judge navigates to the published Application URL
- **THEN** the Gradio app loads in-browser and both tabs (single-video,
  batch) are usable without any local setup
