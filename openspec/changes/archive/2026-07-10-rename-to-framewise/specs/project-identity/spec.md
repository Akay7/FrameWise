## ADDED Requirements

### Requirement: Consistent project name
The project SHALL present itself as **FrameWise** in every user-facing
surface — the README title, the demo app's UI title, and the deployed demo
service's name — with "Track 2 — Video Captioning Agent" retained as a
descriptive subtitle rather than the primary name.

#### Scenario: README title
- **WHEN** a reader opens `README.md`
- **THEN** the top-level heading reads "FrameWise", with "Track 2 — Video
  Captioning Agent" as a subtitle/description beneath it

#### Scenario: Demo app title
- **WHEN** a visitor opens the demo app in a browser
- **THEN** both the browser tab title (Gradio `Blocks(title=...)`) and the
  in-page heading read "FrameWise"

#### Scenario: Deployed demo service name
- **WHEN** the demo is deployed to Render using `render.yaml`
- **THEN** the service is named `framewise-demo`, giving a
  `framewise-demo.onrender.com` URL
