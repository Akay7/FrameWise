## Why

The project has a `Dockerfile` (linux/amd64, ROCm base) but no automated way to build and publish it. Every image currently has to be built and pushed by hand, which is slow, error-prone, and blocks anyone else (or a hackathon judge) from pulling a known-good image. A GitHub Actions workflow that builds and publishes the image on every relevant change removes that manual step.

## What Changes

- Add a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that:
  - Builds the image defined in `Dockerfile` for `linux/amd64`.
  - Logs in to the GitHub Container Registry (`ghcr.io`) using the built-in `GITHUB_TOKEN` (no new secrets required).
  - Publishes the image to `ghcr.io/<owner>/<repo>` tagged with the git ref (branch name, semver tag, and `latest` on the default branch) and the commit SHA.
  - Runs on pushes to the default branch, on version tags (`v*`), and can be triggered manually (`workflow_dispatch`).
  - Uses layer caching (GitHub Actions cache) to keep build times reasonable given the large ROCm/model-weight layers.
- No changes to application code, `Dockerfile` contents, or runtime behavior — this only adds CI plumbing.

## Capabilities

### New Capabilities
- `ci-docker-publish`: Automated CI pipeline that builds the project's Docker image and publishes it to GitHub Container Registry on qualifying triggers.

### Modified Capabilities
- None.

## Impact

- Affected paths: new file `.github/workflows/docker-publish.yml`.
- Affected systems: GitHub Actions (uses default `GITHUB_TOKEN` permissions elevated to `packages: write`), GitHub Container Registry (new package `ghcr.io/<owner>/<repo>`).
- No impact to existing application code, dependencies, or the Dockerfile itself.
- Repo currently has no `git remote` configured; workflow uses `${{ github.repository }}` / `${{ github.repository_owner }}` so it works regardless of remote naming once pushed to GitHub.
