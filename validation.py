"""FrameWise — output-contract validator for the Track 2 agent.

Single source of truth for what a valid ``results.json`` looks like, per the
hackathon contract:

  * top level is a JSON array
  * exactly one result object per input task, matched by ``task_id``
  * no missing or extra ``task_id``s
  * each result has a ``captions`` object with a non-empty string for every
    style its task requested

Used by the container output test and, optionally, by ``main.py`` as a
post-run self-check.
"""

import json

ALL_STYLES = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]


def validate_results(tasks, results) -> list:
    """Return a list of human-readable contract errors; empty means valid.

    ``tasks`` and ``results`` are already-parsed Python objects (lists of
    dicts). Shape problems are reported rather than raised.
    """
    errors = []

    if not isinstance(tasks, list):
        return ["tasks: expected a JSON array at the top level"]
    if not isinstance(results, list):
        return ["results: expected a JSON array at the top level"]

    # Requested styles per task_id (fall back to all four if unspecified).
    wanted = {}
    for i, task in enumerate(tasks):
        if not isinstance(task, dict) or "task_id" not in task:
            errors.append(f"tasks[{i}]: missing 'task_id'")
            continue
        tid = task["task_id"]
        styles = task.get("styles") or ALL_STYLES
        wanted[tid] = list(styles)

    # Index results by task_id, flagging duplicates.
    by_id = {}
    for i, res in enumerate(results):
        if not isinstance(res, dict) or "task_id" not in res:
            errors.append(f"results[{i}]: missing 'task_id'")
            continue
        tid = res["task_id"]
        if tid in by_id:
            errors.append(f"results: duplicate result for task_id '{tid}'")
        by_id[tid] = res

    # Every task must have exactly one well-formed result.
    for tid, styles in wanted.items():
        res = by_id.get(tid)
        if res is None:
            errors.append(f"results: missing result for task_id '{tid}'")
            continue
        captions = res.get("captions")
        if not isinstance(captions, dict):
            errors.append(f"task '{tid}': 'captions' must be an object")
            continue
        for style in styles:
            val = captions.get(style)
            if not isinstance(val, str) or not val.strip():
                errors.append(
                    f"task '{tid}': caption for style '{style}' is missing or empty"
                )

    # Results for tasks that were never requested.
    for tid in by_id:
        if tid not in wanted:
            errors.append(f"results: unexpected result for unknown task_id '{tid}'")

    return errors


def load_and_validate(tasks_path: str, results_path: str) -> list:
    """Read both files and validate; JSON/shape errors come back as the list."""
    try:
        with open(tasks_path) as f:
            tasks = json.load(f)
    except FileNotFoundError:
        return [f"tasks file not found: {tasks_path}"]
    except json.JSONDecodeError as e:
        return [f"tasks file is not valid JSON: {e}"]

    try:
        with open(results_path) as f:
            results = json.load(f)
    except FileNotFoundError:
        return [f"results file not found: {results_path}"]
    except json.JSONDecodeError as e:
        return [f"results file is not valid JSON: {e}"]

    return validate_results(tasks, results)
