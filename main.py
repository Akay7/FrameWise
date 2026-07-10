"""FrameWise — Track 2 — Video Captioning Agent.

Reads /input/tasks.json, generates a caption per requested style for every clip
by calling an external vision model, and writes /output/results.json.

Design:
  * The caption provider (Gemini / OpenAI / Anthropic) is selected at runtime via
    CAPTION_PROVIDER and loaded once, up front — a missing key or unknown
    provider fails the run immediately rather than emitting empty captions.
  * One provider call per clip: the whole clip (native video, where supported)
    or interior-sampled frames, asking for ALL requested styles at once as strict
    JSON. Every caption is grounded in the same observed facts.
  * Pure external: no local model, no fabricated fallback captions. On an
    unrecoverable provider failure the run exits non-zero, but the JSON it writes
    is always well-formed.
"""

import concurrent.futures
import json
import logging
import os
import sys
import tempfile
import time

from media import download_video, probe_duration
from providers import ALL_STYLES, get_provider

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
# The container has no shared-instance memory cap (unlike the Render demo,
# see app.py's DEMO_MAX_PARALLEL_TASKS), so it defaults to real parallelism.
MAX_PARALLEL_TASKS = int(os.environ.get("MAX_PARALLEL_TASKS", "10"))


def _load_baked_env() -> None:
    """Load an optional build-time key file (NAME=VALUE per line).

    Off by default; only present if the image was built with the BAKE_* build
    args. Runtime environment variables always win over baked values.
    """
    path = os.environ.get("BAKED_ENV_FILE", "")
    if not path or not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip())


def process_task(task: dict, provider) -> dict:
    task_id = task.get("task_id", "unknown")
    video_url = task["video_url"]
    styles = task.get("styles") or ALL_STYLES

    logger.info("Task %s | styles=%s", task_id, styles)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        video_path = download_video(video_url, tmp)
        duration = probe_duration(video_path)
        logger.info("Task %s | probed duration: %.1fs", task_id, duration)
        captions = provider.caption_clip(video_path, duration, styles)

    logger.info("Task %s done in %.1fs", task_id, time.time() - t0)
    for s in styles:
        logger.info("Task %s | [%s] %s", task_id, s, captions.get(s, "")[:120])
    return {"task_id": task_id, "captions": captions}


def run_tasks(tasks: list, provider) -> tuple:
    """Run every task through `provider`, never fabricating a caption.

    Shared by main.py (container entrypoint) and app.py (demo UI) so both
    exercise the exact same per-task pipeline. Returns (results, failed)
    where `results` has exactly one entry per input task (matched by
    `task_id`) and `failed` lists the task_ids that errored. Tasks run
    concurrently, up to MAX_PARALLEL_TASKS at once; result order does not
    matter since callers match entries by `task_id`.
    """
    results = []
    failed = []
    workers = min(len(tasks), MAX_PARALLEL_TASKS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(process_task, task, provider): task for task in tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            task_id = task.get("task_id", "unknown")
            styles = task.get("styles") or ALL_STYLES
            try:
                results.append(future.result())
            except Exception as e:  # noqa: BLE001
                logger.exception("Task %s failed: %s", task_id, e)
                failed.append(task_id)
                # Record the task with empty captions — never fabricate text.
                # Keeps the output a well-formed array with one entry per task.
                results.append({"task_id": task_id, "captions": {s: "" for s in styles}})
    return results, failed


def main() -> int:
    start = time.time()
    _load_baked_env()
    logger.info("Loading tasks from %s", INPUT_PATH)
    with open(INPUT_PATH) as f:
        tasks = json.load(f)

    # Load and validate the provider before touching any task. get_provider
    # raises SystemExit on an unknown provider or a missing API key.
    provider = get_provider()

    results, failed = run_tasks(tasks, provider)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d results to %s (%.1fs total)",
                len(results), OUTPUT_PATH, time.time() - start)

    # Self-check the output against the contract (warn only).
    try:
        from validation import validate_results

        errors = validate_results(tasks, results)
        if errors:
            logger.warning("Output failed the contract self-check:")
            for e in errors:
                logger.warning("  - %s", e)
        else:
            logger.info("Output self-check passed.")
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not run output self-check: %s", e)

    if failed:
        logger.error("%d task(s) failed at the provider: %s", len(failed), failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
