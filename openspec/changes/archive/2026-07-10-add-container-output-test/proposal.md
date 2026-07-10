## Why

The agent's only real contract with the hackathon harness is: read `/input/tasks.json`, run the container, and produce a valid `/output/results.json` with a caption for every requested style. Today nothing verifies that end-to-end — a broken entrypoint, a schema regression, or a missing style key would only be discovered at submission time, where it scores zero. We need a repeatable test that runs the built container and asserts the output matches the required contract.

## What Changes

- Add an **end-to-end container test** that runs the built image against a small `tasks.json` fixture and asserts `/output/results.json` satisfies the harness contract (valid JSON; one result per task; every requested style present and a non-empty string; exit code 0).
- Add a lightweight **output-schema validator** the test uses, so the same contract check can also be reused as a post-run self-check.
- Put **all test code and fixtures in a dedicated top-level directory** (e.g. `tests/`) that is excluded from the Docker build context via `.dockerignore`, so tests never bloat the image or count against the 10 GB cap.
- **Document the test** in `README.md`: how to build the image and run the test, and what the test asserts.

## Capabilities

### New Capabilities
- `container-output-test`: An automated end-to-end test that runs the container image and validates its `/output/results.json` against the hackathon output contract, plus the reusable output-schema validator and its README documentation.

### Modified Capabilities
<!-- None: no existing spec-level behavior changes. -->

## Impact

- **New files**: `tests/` directory (test runner/script + `tasks.json` fixture + validator, or the validator may live in the app package and be imported by the test).
- **Modified files**: `.dockerignore` (exclude `tests/`), `README.md` (document the test), and possibly a small validation helper importable by `main.py`.
- **No change** to the runtime captioning pipeline or model.
- **Tooling**: test requires Docker to build/run the image; a fast "logic-only" path should be runnable without a GPU (using a fixture/mocked result) so the contract check is exercisable in CI and on non-AMD machines.
