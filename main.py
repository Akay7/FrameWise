"""Track 2 — Video Captioning Agent.

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

import json
import os
import sys
import tempfile
import time
import traceback

from media import download_video, probe_duration
from providers import ALL_STYLES, get_provider

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")


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

    print(f"\n{'=' * 60}\nTask {task_id} | styles={styles}\n{'=' * 60}")
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        video_path = download_video(video_url, tmp)
        duration = probe_duration(video_path)
        captions = provider.caption_clip(video_path, duration, styles)

    print(f"Task {task_id} done in {time.time() - t0:.1f}s")
    for s in styles:
        print(f"  [{s}] {captions.get(s, '')[:120]}")
    return {"task_id": task_id, "captions": captions}


def main() -> int:
    start = time.time()
    _load_baked_env()
    print(f"Loading tasks from {INPUT_PATH}")
    with open(INPUT_PATH) as f:
        tasks = json.load(f)

    # Load and validate the provider before touching any task. get_provider
    # raises SystemExit on an unknown provider or a missing API key.
    provider = get_provider()

    results = []
    failed = []
    for task in tasks:
        task_id = task.get("task_id", "unknown")
        styles = task.get("styles") or ALL_STYLES
        try:
            results.append(process_task(task, provider))
        except Exception as e:  # noqa: BLE001
            print(f"ERROR on task {task_id}: {e}")
            traceback.print_exc()
            failed.append(task_id)
            # Record the task with empty captions — never fabricate text. Keeps
            # the output a well-formed array with one entry per task.
            results.append({"task_id": task_id, "captions": {s: "" for s in styles}})

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(results)} results to {OUTPUT_PATH} "
          f"({time.time() - start:.1f}s total)")

    # Self-check the output against the contract (warn only).
    try:
        from validation import validate_results

        errors = validate_results(tasks, results)
        if errors:
            print("WARNING: output failed the contract self-check:")
            for e in errors:
                print("  -", e)
        else:
            print("Output self-check passed.")
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: could not run output self-check: {e}")

    if failed:
        print(f"ERROR: {len(failed)} task(s) failed at the provider: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
