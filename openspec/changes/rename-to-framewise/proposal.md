## Why

The project has an actual name — **FrameWise** — already used as the
headline in `presentation/slides.md`, but everywhere else (README, package
metadata, module docstrings, the demo app's title, the Render service name)
still uses the generic working title "Track 2 — Video Captioning Agent" /
`video-captioning-agent`. Naming the submission consistently makes it
recognizable to judges across the deck, the README, the live demo UI, and
the deployed URL.

## What Changes

- Rename the project to **FrameWise** across user-facing text: `README.md`
  title/headers, the demo app's UI title (`app.py`), and module docstrings
  (`main.py`, `providers.py`, `media.py`, `validation.py`, `app.py`) —
  each keeps "Track 2 — Video Captioning Agent" as a descriptive subtitle
  under the FrameWise name, matching the pattern already used in
  `presentation/slides.md`.
- Rename the Python package: `pyproject.toml`'s `name` field changes from
  `video-captioning-agent` to `framewise`.
- Rename the Render demo service from `video-captioning-agent-demo` to
  `framewise-demo` in `render.yaml` (this is the name Render derives the
  public URL from: `framewise-demo.onrender.com`).
- Update the documented GHCR pull path in `README.md` from
  `ghcr.io/akay7/amd-act2-track2-video_captioning_agent` to
  `ghcr.io/akay7/framewise`, since the publish workflow
  (`.github/workflows/docker-publish.yml`) derives the image path from the
  GitHub repository name (`${{ github.repository }}`, lowercased) — this
  documentation update is only accurate once the GitHub repository itself
  is renamed, which is a manual, external action outside this change's
  scope (see design.md).

## Capabilities

### New Capabilities
- `project-identity`: the project presents itself consistently as
  "FrameWise" across the README, the demo app's UI title, and the deployed
  demo service name.

### Modified Capabilities
<!-- None: no requirement or scenario changes to demo-web-app. Its UI title
     text and Render service name change as a side effect of the naming
     requirement above, but no behavior, input, or output it describes
     changes. -->

## Impact

- **Code**: `pyproject.toml` (`name`), `render.yaml` (`name`), `app.py`
  (Gradio `Blocks(title=...)` and the H1 markdown), module docstrings in
  `main.py`/`providers.py`/`media.py`/`validation.py`/`app.py`.
- **Docs**: `README.md` title/headers and the GHCR pull command;
  `presentation/slides.md` already uses "FrameWise" and needs no change.
- **Deployment**: no functional change — `Dockerfile`/`Dockerfile.demo`
  build the same image, just under a renamed Render service. The GHCR
  image path only changes once the GitHub repository is renamed (manual,
  outside this change).
- **Out of scope**: actually renaming the GitHub repository (a shared,
  hard-to-reverse action affecting clone URLs and existing links) is not
  performed by this change — it's called out as a manual follow-up in
  design.md/tasks.md.
