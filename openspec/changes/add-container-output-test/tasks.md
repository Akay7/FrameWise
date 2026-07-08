## 1. Output contract validator

- [x] 1.1 Add `validation.py` with `validate_results(tasks, results) -> list[str]` that checks: top-level JSON array, one result per task matched by `task_id`, no extra/missing `task_id`s, and a non-empty string `captions[style]` for every style each task requests.
- [x] 1.2 Add a `load_and_validate(tasks_path, results_path) -> list[str]` helper that reads both files, handles JSON parse/shape errors, and returns the error list.

## 2. Test directory and fixtures

- [x] 2.1 Create top-level `tests/` directory.
- [x] 2.2 Add `tests/fixtures/tasks.json` with one short-clip task requesting all four styles.
- [x] 2.3 Add `tests/fixtures/results_good.json` and `tests/fixtures/results_bad.json` (missing style, extra/missing task, malformed) for the contract test.

## 3. Contract test (fast, no GPU)

- [x] 3.1 Add `tests/test_contract.py` that imports the validator and asserts the good fixture passes and each bad fixture fails with the expected offending `task_id`/style.
- [x] 3.2 Verify it runs with no GPU/Docker (`python -m pytest tests/test_contract.py` or `python tests/test_contract.py`).

## 4. End-to-end container test (Docker + GPU)

- [x] 4.1 Add `tests/run_e2e.py` (or `tests/test_e2e.py`) that `docker run`s the image with `tests/fixtures/tasks.json` mounted at `/input/tasks.json` and a temp dir at `/output`, then asserts exit 0 and validates the produced `/output/results.json`.
- [x] 4.2 Gate the e2e test behind an env flag / skip marker (e.g. `RUN_E2E=1`) and allow the image tag and fixture URL to be overridden via env.
- [x] 4.3 Surface container exit code and logs on failure.

## 5. Exclude tests from Docker build

- [x] 5.1 Add `tests/` to `.dockerignore`.
- [x] 5.2 Confirm the built image does not contain `tests/` (spot-check the build context or image contents).

## 6. Optional runtime self-check

- [x] 6.1 In `main.py`, after writing `results.json`, call the validator and log any contract errors (warn, do not delete output).

## 7. Documentation

- [x] 7.1 Add a "Testing" section to `README.md` covering the contract test command, the e2e test command and its prerequisites (Docker, AMD GPU, network), and what the test asserts.
- [x] 7.2 Note in `README.md` that tests live in `tests/` and are excluded from the Docker image.

## 8. Verify

- [x] 8.1 Run the contract test and confirm pass.
- [x] 8.2 Where hardware allows, build the image and run the e2e test; confirm exit 0 and a valid `results.json`.
- [x] 8.3 Run `openspec validate add-container-output-test --strict` and fix any issues.
