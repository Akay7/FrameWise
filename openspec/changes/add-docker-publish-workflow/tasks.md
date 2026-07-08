## 1. Workflow scaffolding

- [x] 1.1 Create `.github/workflows/docker-publish.yml` with `name`, `permissions: { contents: read, packages: write }`, and triggers: `push` to default branch, `push` tags `v*`, and `workflow_dispatch`.
- [x] 1.2 Define the single job `build-and-push` running on `ubuntu-latest`.

## 2. Build steps

- [x] 2.1 Add `actions/checkout@v4` step.
- [x] 2.2 Add `docker/setup-buildx-action@v3` step.
- [x] 2.3 Add `docker/login-action@v3` step targeting `ghcr.io`, using `github.actor` and `secrets.GITHUB_TOKEN`.
- [x] 2.4 Add `docker/metadata-action@v5` step producing tags for: default-branch `latest`, branch name, semver (`vX.Y.Z` → `X.Y.Z` and `X.Y`), and short commit SHA; image name `ghcr.io/${{ github.repository }}`.
- [x] 2.5 Add `docker/build-push-action@v6` step: `context: .`, `platforms: linux/amd64`, `push: true` only when not a pull request event, `tags`/`labels` from the metadata step output, `cache-from: type=gha`, `cache-to: type=gha,mode=max`.

## 3. Verification

- [ ] 3.1 Push the workflow file to a branch and trigger it via `workflow_dispatch` (or push to default branch) to confirm the build succeeds within GitHub-hosted runner disk limits (see design.md open question on runner disk space).
- [ ] 3.2 Confirm the image appears under `ghcr.io/<owner>/<repo>` with the expected tags (`latest` + SHA on default branch).
- [ ] 3.3 If the first publish creates a private/unlinked package, link the GHCR package to the repository and set its visibility as intended (e.g. public) via the package settings.
- [ ] 3.4 Push a test tag (e.g. `v0.0.1-test`) to confirm semver tagging works, then delete the test tag and the corresponding test image version if not wanted.

## 4. Documentation

- [x] 4.1 Add a short section to the README (or create one if absent) documenting the published image location (`ghcr.io/<owner>/<repo>`) and how to pull/run it.
