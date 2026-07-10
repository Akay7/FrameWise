# container-output-test

## Purpose

Verify that the packaged container image produces output that conforms to the hackathon output contract, via a reusable validator and an automated end-to-end container test, without bloating the shipped image with test code.

## Requirements

### Requirement: Output contract validator

The system SHALL provide a reusable validator that checks a `results.json` payload against the hackathon output contract. The validator MUST verify that the payload is a JSON array, that it contains exactly one result object per input task (matched by `task_id`), and that each result object contains a `captions` object with a non-empty string for every style requested by the corresponding task.

#### Scenario: Valid results pass

- **WHEN** the validator is given a tasks fixture and a `results.json` where every task has a matching result whose `captions` include a non-empty string for each requested style
- **THEN** the validator reports success with no errors

#### Scenario: Missing style fails

- **WHEN** a result object omits a style that its task requested, or maps that style to an empty string
- **THEN** the validator reports failure and identifies the offending `task_id` and style

#### Scenario: Missing or extra task fails

- **WHEN** the results array is missing a result for a requested `task_id`, or contains a result for a `task_id` not present in the tasks fixture
- **THEN** the validator reports failure and names the mismatched `task_id`

#### Scenario: Malformed JSON fails

- **WHEN** the results payload is not valid JSON or is not a JSON array at the top level
- **THEN** the validator reports failure with a clear parse/shape error

### Requirement: End-to-end container test

The system SHALL provide an automated test that builds or uses the container image, runs it with a small tasks fixture mounted at `/input/tasks.json` and an empty output directory mounted at `/output`, and asserts that the container exits with code 0 and writes an `/output/results.json` that passes the output contract validator.

#### Scenario: Container produces valid output

- **WHEN** the test runs the image against the tasks fixture
- **THEN** the container exits 0 and the resulting `/output/results.json` passes the output contract validator for that fixture

#### Scenario: Container failure is surfaced

- **WHEN** the container exits non-zero or writes no `/output/results.json`
- **THEN** the test fails and surfaces the container's exit code and logs

### Requirement: Tests excluded from Docker build context

Test code and fixtures SHALL live in a dedicated top-level directory that is excluded from the Docker build context via `.dockerignore`, so that test assets never enter the image or count against the image size cap.

#### Scenario: Test directory is ignored by the build

- **WHEN** the Docker image is built
- **THEN** the dedicated test directory and its contents are not copied into the image

### Requirement: Test documented in README

The `README.md` SHALL document how to run the container output test, including the build/run commands and a description of what the test asserts.

#### Scenario: README describes the test

- **WHEN** a developer reads `README.md`
- **THEN** they find the command(s) to run the test and a summary of the contract the test enforces
