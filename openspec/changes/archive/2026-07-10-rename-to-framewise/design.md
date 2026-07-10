## Context

"FrameWise" is already the project's real name — it's the headline in
`presentation/slides.md` — but the README, package metadata, module
docstrings, the demo app's title, and the Render service name all still
carry the placeholder "Track 2 — Video Captioning Agent" /
`video-captioning-agent`. This is a naming/rebrand change touching many
files but no runtime behavior: every requirement in
`specs/demo-web-app/spec.md` (single-video tab, batch tab, user-supplied
credentials, hosted demo) continues to work exactly as before — only
strings change.

## Goals / Non-Goals

**Goals:**
- One consistent name ("FrameWise") visible everywhere a human reads it:
  README, demo UI, module docstrings, Render service/URL, slides (already
  done).
- Keep "Track 2 — Video Captioning Agent" as a subtitle/description under
  the FrameWise name where it adds context (matches the pattern already
  established in `presentation/slides.md`), rather than deleting it.

**Non-Goals:**
- No behavior change — this touches strings only (titles, docstrings, a
  package name, a Render service name).
- **Not renaming the actual GitHub repository.** That's a shared,
  hard-to-reverse action (breaks existing clone URLs/links for anyone who
  has them, requires updating any external references, and GitHub's
  redirect-on-rename doesn't cover every case e.g. `git@` SSH remotes some
  tooling has cached). It's called out as a manual follow-up, not performed
  by this change.
- Not touching the already-published GHCR tags under the current path —
  old tags stay where they are; only the README's *documented* pull path
  is updated, and only once the repo rename actually happens.

## Decisions

- **Package name**: `pyproject.toml`'s `name` field becomes `framewise`
  (was `video-captioning-agent`). The package isn't published to PyPI, so
  this is purely cosmetic/consistency, not a breaking change for anyone.
- **Render service name**: `render.yaml`'s `name` becomes `framewise-demo`
  (was `video-captioning-agent-demo`), giving a
  `framewise-demo.onrender.com` URL once deployed. Confirmed over the
  literal "FrameWide-demo" from the request — treated as a typo for
  FrameWise, since a mismatched public URL would be confusing and hard to
  fix quietly after judges have the link.
- **GHCR path documentation**: the publish workflow
  (`.github/workflows/docker-publish.yml`) already derives the image path
  from `${{ github.repository }}` (lowercased) — it needs no code change.
  The README's *documented* pull command is updated to the presumed
  post-rename path `ghcr.io/akay7/framewise`, with an explicit note that
  it's only accurate once the GitHub repository is renamed to `FrameWise`
  (manual step, see Migration Plan) — avoids the doc silently drifting
  from what `docker pull` will actually resolve to in the meantime.
- **Docstring pattern**: module docstrings keep the descriptive line
  ("Track 2 — Video Captioning Agent...") but are prefixed with "FrameWise
  — " so a reader opening any file sees the project name immediately,
  consistent with the README/UI.

## Risks / Trade-offs

- [README's GHCR pull command is temporarily inaccurate if this change
  ships before the GitHub repo is actually renamed] → The command is
  annotated with a comment noting it takes effect after the repo rename;
  until then, `ghcr.io/akay7/amd-act2-track2-video_captioning_agent` (the
  currently-published path) still works and is not deleted from history.
- [Renaming the Render service name after a service already exists under
  the old name would require deleting/recreating it, not just editing
  `render.yaml`] → Not a live risk yet: per the still-open deploy tasks in
  `add-gradio-demo-app`, no Render service has been created yet, so this
  change lands before that manual step, not after.

## Migration Plan

1. Update `pyproject.toml`, `render.yaml`, `app.py`, module docstrings,
   and `README.md` per the Decisions above.
2. (Manual, outside this change, whenever the user chooses to do it):
   rename the GitHub repository to `FrameWise` — after that, the CI
   workflow automatically publishes to `ghcr.io/akay7/framewise` with no
   further code change, matching the README's documented path.
3. Create the Render service (still pending from `add-gradio-demo-app`)
   using the now-updated `render.yaml`, so it's named `framewise-demo`
   from the start.

No rollback complexity: pure string changes, reversible by re-editing the
same files.

## Open Questions

- None — naming and scope were confirmed before drafting.
