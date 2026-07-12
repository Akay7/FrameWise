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
import traceback

from media import download_video, probe_duration
from providers import ALL_STYLES, get_provider

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
# Frame-based providers run ffmpeg per task (subprocess, releases the GIL),
# so concurrent tasks decode truly in parallel and compete for the same
# CPU/memory budget. Defaults to 2 to match the grading environment's 2 vCPU
# cap — higher values OOM on long (~2.5min) 4K clips at MAX_PARALLEL_TASKS=10
# (verified: 10-way concurrency on 2 vCPU/4GB killed ffmpeg mid-decode for
# some tasks). Raise via env var only on a host with more CPU/memory headroom.
MAX_PARALLEL_TASKS = int(os.environ.get("MAX_PARALLEL_TASKS", "2"))
# Debug knob for bisecting judge-environment crashes stage by stage: 0=read
# input + write output only (no download), 1=+download, 2=+ffmpeg/ffprobe,
# 3=+LLM call, 4=full pipeline (default, unchanged behavior). Baked in at
# build time (like CAPTION_PROVIDER) since the judge harness does not support
# runtime env var injection.
PIPELINE_STAGE = int(os.environ.get("PIPELINE_STAGE", "4"))


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

    logger.info("Task %s | styles=%s | pipeline_stage=%d", task_id, styles, PIPELINE_STAGE)
    t0 = time.time()
    captions = {s: "" for s in styles}
    if PIPELINE_STAGE >= 1:
        with tempfile.TemporaryDirectory() as tmp:
            video_path = download_video(video_url, tmp)
            logger.info("Task %s | stage 1 (download) OK: %.1f MB",
                         task_id, os.path.getsize(video_path) / 1e6)
            if PIPELINE_STAGE >= 2:
                duration = probe_duration(video_path)
                logger.info("Task %s | stage 2 (ffmpeg probe) OK: %.1fs", task_id, duration)
                if PIPELINE_STAGE >= 3:
                    captions = provider.caption_clip(video_path, duration, styles)
                    logger.info("Task %s | stage 3 (LLM) OK", task_id)

    logger.info("Task %s done in %.1fs (stage %d reached)",
                 task_id, time.time() - t0, PIPELINE_STAGE)
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
    # raises SystemExit on an unknown provider or a missing API key. Skipped
    # below stage 3 so download/ffmpeg-only debug images need no API key.
    provider = get_provider() if PIPELINE_STAGE >= 3 else None

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
    if PIPELINE_STAGE >= 4:
        sys.exit(main())

    # Debug bisection build (PIPELINE_STAGE < 4): a plain handled failure
    # (bad task JSON, network error, missing key, etc.) must not look like a
    # crash, so any exception is caught and swallowed with exit 0 here. If the
    # judge harness still reports RUNTIME_ERROR for this image, the failure is
    # outside Python's control (killed process, missing mount, OOM, sandbox
    # network block that hangs rather than raises, etc.) rather than an
    # ordinary handled error.
    try:
        main()
    except BaseException:
        logger.exception("Debug stage %d: unhandled error (exiting 0 anyway)", PIPELINE_STAGE)
        try:
            os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
            with open(OUTPUT_PATH, "w") as f:
                json.dump(
                    {"pipeline_stage": PIPELINE_STAGE, "error": traceback.format_exc()},
                    f, indent=2,
                )
        except Exception:  # noqa: BLE001
            pass
    sys.exit(0)
