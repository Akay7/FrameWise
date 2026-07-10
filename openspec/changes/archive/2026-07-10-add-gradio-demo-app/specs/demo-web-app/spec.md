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

### Requirement: User-supplied provider credentials
The demo app SHALL let each visitor choose a caption provider and enter
their own API key for that provider via the UI, and SHALL use only that
per-request key when calling the provider — it SHALL NOT read a provider
API key from server environment variables or any other server-side source.

#### Scenario: Caption with a user-supplied key
- **WHEN** a user selects a provider, enters their own API key, and
  submits (single-video or batch)
- **THEN** the app calls that provider using only the entered key, and
  does not fall back to a server-configured key

#### Scenario: Missing API key
- **WHEN** a user submits without entering an API key
- **THEN** the app rejects the submission with a validation message and
  does not call any provider

#### Scenario: Invalid API key
- **WHEN** a user submits a key the provider's API rejects
- **THEN** the app surfaces the provider's authentication error to the
  user without echoing the key value back, and does not retain the key
  after the request completes

### Requirement: OpenAI-compatible endpoint override
When the `openai` provider is selected, the demo app SHALL let the user
optionally specify a Base URL and Model, matching the container's
`OPENAI_BASE_URL`/`OPENAI_MODEL` overrides, so a visitor can point the demo
at their own OpenAI-compatible server instead of the public OpenAI API.

#### Scenario: Caption via a custom OpenAI-compatible endpoint
- **WHEN** a user selects the `openai` provider, enters a Base URL (and
  optionally a Model), and submits
- **THEN** the app sends requests to that Base URL instead of the default
  OpenAI API

#### Scenario: API key optional with a custom Base URL
- **WHEN** a user has entered a Base URL for the `openai` provider but
  leaves the API key field empty
- **THEN** the app still allows the submission, using a placeholder
  credential for the request, consistent with the container's handling of
  local OpenAI-compatible servers

### Requirement: Hosted, publicly reachable demo
The demo app SHALL be deployed to a hosting platform that provides a
stable public URL reachable without the visitor installing Docker or
cloning the repository.

#### Scenario: Judge opens the demo URL
- **WHEN** a judge navigates to the published Application URL
- **THEN** the Gradio app loads in-browser and both tabs (single-video,
  batch) are usable without any local setup
