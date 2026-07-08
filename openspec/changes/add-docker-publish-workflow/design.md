## Context

The repo builds a single Docker image (`Dockerfile`) that bakes in ROCm PyTorch and Qwen2.5-VL-3B weights ([[track2-architecture]] constraint: image must stay under the 10GB compressed cap). There is no CI today — no `.github/workflows/` directory exists. The image is large and slow to build (model download + ROCm wheels), so the workflow needs to be mindful of build minutes and caching. No container registry is configured yet; GHCR is the natural default since it requires no external account setup and works with the repo's built-in `GITHUB_TOKEN`.

## Goals / Non-Goals

**Goals:**
- Build the existing `Dockerfile` unmodified, for `linux/amd64`.
- Push the resulting image to `ghcr.io/<owner>/<repo>` automatically on push to the default branch and on version tags.
- Tag images predictably: branch name, `latest` (default branch only), semver tags (`vX.Y.Z` pushes), and short commit SHA.
- Allow manual re-runs via `workflow_dispatch` (useful since a first-time push must also make the GHCR package visible/linked).
- Use build caching to avoid re-downloading model weights / re-installing ROCm wheels on every run where layers haven't changed.

**Non-Goals:**
- Multi-arch builds (linux/arm64) — the base project targets linux/amd64 ROCm hosts only.
- Publishing to Docker Hub or any registry other than GHCR.
- Automated deployment/rollout of the published image — this workflow only builds and publishes it.
- Changing the Dockerfile's contents, base image, or model baked into it.

## Decisions

- **Registry: GHCR (`ghcr.io`) over Docker Hub.** Uses the repo's built-in `GITHUB_TOKEN` (`packages: write` permission) — no secrets to provision. Docker Hub would require a separate account and PAT stored as a secret, with no benefit for this use case.
- **Build action: `docker/build-push-action@v6` with `docker/setup-buildx-action` and `docker/login-action`.** These are the standard, actively maintained GitHub-provided actions for Docker builds; avoids hand-rolling `docker build`/`docker push` shell steps and gets GHA cache support for free.
- **Tagging: `docker/metadata-action@v5`** to derive tags (branch, semver, sha, `latest`) instead of hand-written bash, since it correctly handles the default-branch-only `latest` tag and semver tag parsing.
- **Trigger: `push` to default branch + `push` tags `v*` + `workflow_dispatch`.** No PR builds — building/pushing on every PR would spam the registry with throwaway tags and cost significant build minutes given the large image; PR validation of the Dockerfile (if wanted later) would be a separate, non-publishing job.
- **Caching: GitHub Actions cache (`cache-from`/`cache-to: type=gha`)** rather than registry-based cache, since it's simpler to wire up and sufficient for a single-branch-mostly workflow. Trade-off noted below.
- **Single job, single platform.** Given the 10GB image-size constraint and ROCm-specific base, matrix builds across platforms/ROCm versions are out of scope; the existing `ROCM_INDEX` build-arg remains a manual override, not a matrix dimension.

## Risks / Trade-offs

- **[Risk] GitHub Actions cache has a 10GB per-repo eviction limit and this image's layers are large (ROCm + model weights).** → Mitigation: cache is best-effort; a cold cache just means a full rebuild (slower, not broken). Acceptable since publishes are infrequent (push to main / tags only).
- **[Risk] Build minutes / runner disk space: default GitHub-hosted runners have ~14GB free disk, and this image bakes in multi-GB model weights plus ROCm torch wheels, which could approach or exceed runner disk limits.** → Mitigation: document this in tasks.md as something to verify on first run; if it fails, the fallback is a larger runner (`runs-on: ubuntu-latest-4-cores` or self-hosted) — noted as an open question below.
- **[Risk] First-time GHCR packages are private by default and linked to the pushing actor, not the repo, until manually connected.** → Mitigation: task list includes a manual step to link/make the package visibility match the repo after first publish.
- **[Trade-off] No PR-triggered build validation** means a broken Dockerfile is only caught on push to main/tag, not in review. Acceptable for now given cost; can be added later as a separate non-publishing "build only" job if desired.

## Open Questions

- Does the default GitHub-hosted runner have enough disk space for this image's build (ROCm wheels + baked-in model weights)? To be verified on first workflow run; escalate to a larger runner if it fails.
