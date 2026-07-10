## 1. Package and deployment metadata

- [x] 1.1 `pyproject.toml`: change `name` from `video-captioning-agent` to `framewise`
- [x] 1.2 `render.yaml`: change the service `name` from `video-captioning-agent-demo` to `framewise-demo`

## 2. Demo app

- [x] 2.1 `app.py`: change `gr.Blocks(title=...)` to `"FrameWise — Demo"` (or similar)
- [x] 2.2 `app.py`: change the in-page `gr.Markdown` H1 from "Video Captioning Agent — Demo" to lead with "FrameWise"
- [x] 2.3 `app.py`: update the module docstring to lead with "FrameWise"

## 3. Module docstrings

- [x] 3.1 `main.py`: update module docstring to lead with "FrameWise", keeping "Track 2 — Video Captioning Agent" as a subtitle/description
- [x] 3.2 `providers.py`: same docstring update
- [x] 3.3 `media.py`: same docstring update
- [x] 3.4 `validation.py`: same docstring update

## 4. README

- [x] 4.1 Change the top-level heading from "Track 2 — Video Captioning Agent" to "FrameWise", with the old text retained as a subtitle line beneath it
- [x] 4.2 Update the documented GHCR pull path to `ghcr.io/akay7/framewise`, with a note that it takes effect once the GitHub repository is renamed (manual, outside this change) — do not remove the still-accurate current path until that happens (kept the current path, added an explanatory note rather than swapping it, since swapping would make the doc inaccurate today)
- [x] 4.3 Update the Render deploy section's example service name/URL to `framewise-demo` / `framewise-demo.onrender.com`

## 5. Verify

- [x] 5.1 `python -m py_compile app.py main.py providers.py media.py validation.py` to confirm no syntax errors from docstring edits
- [x] 5.2 Re-run `tests/test_contract.py` and `tests/test_providers.py` to confirm no behavior changed
- [x] 5.3 Grep the repo for remaining "video-captioning-agent" / "Video Captioning Agent" occurrences outside of intentional subtitle text, and confirm each is either an intentional subtitle or genuinely out of scope (e.g. the current, still-published GHCR path) — also renamed the two locally-chosen Docker build-tag examples in README (`docker build -t framewise .`) for consistency, since those aren't tied to any published resource. Left `Dockerfile`'s comment header and `presentation/slides.md`'s CI-target/footline mentions untouched — not enumerated in the proposal's file list and either already-accurate published paths or low-value churn on a deck that would need PDF regeneration again.

## 6. Manual follow-up (outside this change)

- [ ] 6.1 Rename the GitHub repository to `FrameWise` when ready — **manual**: a shared, hard-to-reverse action; not performed automatically. After this, the CI workflow (`.github/workflows/docker-publish.yml`) publishes to `ghcr.io/akay7/framewise` with no further code change, matching the README update from 4.2.
