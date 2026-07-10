## Context

The agent is a batch container: it reads `/input/tasks.json`, produces `/output/results.json`, and exits. The hackathon harness scores zero for malformed output or any missing style, so the output contract is the single most important invariant to protect. There is currently no automated check of that contract.

Two constraints shape the design:
- The real pipeline needs an AMD ROCm GPU and a multi-GB image, so a full container run is slow and not runnable on arbitrary dev machines / CI.
- The image must stay under the 10 GB compressed cap, so nothing test-related may enter the build context.

## Goals / Non-Goals

**Goals:**
- A single source-of-truth validator for the output contract, importable by both the test and (optionally) `main.py` as a post-run self-check.
- A fast contract test that runs anywhere (no GPU) by validating a produced/fixture `results.json`.
- A full end-to-end test that actually runs the built image and validates its real output.
- Keep all test assets out of the Docker image.
- Document the test in `README.md`.

**Non-Goals:**
- Judging caption *quality* (accuracy/style) — that is the hidden LLM judge's job, not this test.
- Mocking the VLM to produce plausible captions; the fast path only checks structure, not content quality.
- CI wiring (a follow-up; this change delivers the runnable test + docs).

## Decisions

**1. Validator lives in the app package, not only in tests.**
Put a `validate_results(tasks, results) -> list[str]` (returns errors; empty = pass) in an importable module (e.g. `validation.py`). Rationale: single definition of the contract, reused by the test and optionally by `main.py` to self-check before exit. Alternative (validator only inside `tests/`) rejected because `main.py` can't then reuse it, and `tests/` is `.dockerignore`d so it can't be imported at runtime.

**2. Two-tier test.**
- *Contract test* (fast, no GPU): feed the validator a tasks fixture + a `results.json` and assert pass/fail on good and bad payloads. Runs in CI and on any laptop.
- *End-to-end test* (Docker + GPU): `docker run` the image with the fixture mounted, assert exit 0 and validate the real `/output/results.json`. Gated behind an env flag / marker so it's skipped where Docker/GPU is unavailable.
Rationale: the contract test gives constant, portable protection against schema regressions; the e2e test gives true confidence but only where the hardware exists.

**3. Tests as a plain `tests/` directory, excluded via `.dockerignore`.**
Add `tests/` to `.dockerignore`. The e2e runner can be a small Python script (`pytest` optional) so no test dependency is added to the image. Rationale: honors the "separate directory ignored by docker build" requirement and protects the size cap.

**4. Fixture uses one short task with all four styles.**
Keep the fixture minimal (one clip URL, all four styles) to keep the e2e run within time limits while still exercising every style key. Use a small/short public clip for speed.

## Risks / Trade-offs

- [E2e test needs GPU + network + large image → not runnable in generic CI] → Split into the always-on contract test and the opt-in e2e test; document the hardware/network prerequisites for the latter.
- [`.dockerignore` mistake silently ships tests into the image] → Add an assertion/among the e2e checks (or a doc note) and keep the ignore entry explicit and reviewed.
- [Validator drift from the real harness contract] → Base the validator strictly on the documented contract (array, per-task `task_id`, `captions` with non-empty string per requested style) and keep it the one place that encodes it.
- [Real clip download flakiness in the e2e run] → Allow the fixture URL to be overridden; keep the contract test independent of any network.

## Open Questions

- Should `main.py` call the validator before exit and hard-fail on a broken contract, or only warn? (Leaning: warn + still write output, since partial output may still score.)
- `pytest` vs a plain `python tests/run_*.py` script for the runner — pick whichever keeps the repo dependency-light; not blocking.
