## ADDED Requirements

### Requirement: Automated image build on qualifying triggers
The system SHALL automatically build the project's `Dockerfile` for `linux/amd64` via a GitHub Actions workflow whenever a commit is pushed to the default branch, whenever a tag matching `v*` is pushed, or whenever the workflow is manually triggered.

#### Scenario: Push to default branch
- **WHEN** a commit is pushed to the repository's default branch
- **THEN** the workflow SHALL run and build the Docker image from the repository's `Dockerfile`

#### Scenario: Version tag pushed
- **WHEN** a tag matching `v*` (e.g. `v1.2.0`) is pushed
- **THEN** the workflow SHALL run and build the Docker image from the repository's `Dockerfile`

#### Scenario: Manual trigger
- **WHEN** a maintainer triggers the workflow manually via `workflow_dispatch`
- **THEN** the workflow SHALL run and build the Docker image from the repository's `Dockerfile`

#### Scenario: Pull request opened
- **WHEN** a pull request is opened or updated against the default branch
- **THEN** the workflow SHALL NOT build or publish an image for that pull request event

### Requirement: Publish to GitHub Container Registry
The system SHALL publish a successfully built image to `ghcr.io/<owner>/<repo>` using the workflow's default `GITHUB_TOKEN` for authentication, without requiring any additional secrets to be configured.

#### Scenario: Successful build on default branch
- **WHEN** the Docker image builds successfully from a push to the default branch
- **THEN** the workflow SHALL push the image to `ghcr.io/<owner>/<repo>` tagged with `latest` and the short commit SHA

#### Scenario: Successful build on version tag
- **WHEN** the Docker image builds successfully from a pushed tag matching `v*`
- **THEN** the workflow SHALL push the image to `ghcr.io/<owner>/<repo>` tagged with the semver value (e.g. `1.2.0`, `1.2`) and the short commit SHA, without moving the `latest` tag

#### Scenario: Build failure
- **WHEN** the Docker build step fails for any trigger
- **THEN** the workflow SHALL fail and SHALL NOT push any image to the registry

### Requirement: Build cache reuse
The system SHALL cache Docker build layers between workflow runs using the GitHub Actions cache backend, to avoid redundant re-execution of expensive layers (ROCm wheel installation, model weight download) when the underlying Dockerfile instructions are unchanged.

#### Scenario: Unchanged base layers on subsequent run
- **WHEN** a workflow run occurs after a prior successful run and the layers preceding a Dockerfile change are unchanged
- **THEN** the build SHALL reuse the cached layers instead of re-executing them
