"""Fast, GPU-free contract test for the output validator.

Runs either under pytest (`python -m pytest tests/test_contract.py`) or
standalone (`python tests/test_contract.py`). No Docker, no model, no network.
"""

import json
import os
import sys

# Make the repo-root modules (validation.py) importable when run directly.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from validation import load_and_validate, validate_results  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TASKS = os.path.join(FIXTURES, "tasks.json")


def _load(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


def test_good_results_pass():
    tasks = _load("tasks.json")
    results = _load("results_good.json")
    errors = validate_results(tasks, results)
    assert errors == [], f"expected no errors, got: {errors}"


def test_missing_style_fails():
    errors = load_and_validate(
        TASKS, os.path.join(FIXTURES, "results_bad_missing_style.json")
    )
    assert errors, "expected an error for a missing/empty style"
    joined = " ".join(errors)
    assert "v1" in joined
    # both the empty 'sarcastic' and the absent 'humorous_non_tech' are flagged
    assert "sarcastic" in joined
    assert "humorous_non_tech" in joined


def test_missing_task_fails():
    errors = load_and_validate(
        TASKS, os.path.join(FIXTURES, "results_bad_missing_task.json")
    )
    assert any("missing result for task_id 'v1'" in e for e in errors), errors


def test_extra_task_fails():
    errors = load_and_validate(
        TASKS, os.path.join(FIXTURES, "results_bad_extra_task.json")
    )
    assert any("v99" in e for e in errors), errors


def test_malformed_json_fails():
    errors = load_and_validate(
        TASKS, os.path.join(FIXTURES, "results_bad_malformed.json")
    )
    assert any("not valid JSON" in e for e in errors), errors


def test_top_level_not_array_fails():
    errors = validate_results({"task_id": "v1"}, [])
    assert errors and "array" in errors[0]


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
