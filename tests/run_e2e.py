"""End-to-end container test: run the built image and validate its output.

Requires Docker, network egress, and a valid provider API key (the container
calls an external vision model). Guarded so it is skipped unless explicitly
opted into with RUN_E2E=1.

Environment:
  RUN_E2E=1            enable the test (otherwise it skips and exits 0)
  IMAGE=<tag>          image to run (default: video-caption:latest)
  E2E_TASKS=<path>     tasks fixture to mount (default: tests/fixtures/tasks.json)
  CAPTION_PROVIDER     gemini | openai | anthropic (default: gemini)
  <PROVIDER>_API_KEY   the selected provider's key, passed into the container
  DOCKER_RUN_FLAGS     extra `docker run` flags (default: none)
  E2E_TIMEOUT=<secs>   max seconds for the container run (default: 300)

Usage:
  RUN_E2E=1 IMAGE=video-caption:latest CAPTION_PROVIDER=gemini \
    GEMINI_API_KEY=... python tests/run_e2e.py
"""

import os
import shlex
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from validation import load_and_validate  # noqa: E402

KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def main() -> int:
    if os.environ.get("RUN_E2E") != "1":
        print("SKIP e2e: set RUN_E2E=1 to run the container test.")
        return 0

    image = os.environ.get("IMAGE", "video-caption:latest")
    tasks = os.environ.get(
        "E2E_TASKS", os.path.join(REPO_ROOT, "tests", "fixtures", "tasks.json")
    )
    provider = os.environ.get("CAPTION_PROVIDER", "gemini").lower()
    run_flags = os.environ.get("DOCKER_RUN_FLAGS", "")
    timeout = int(os.environ.get("E2E_TIMEOUT", "300"))

    if not os.path.exists(tasks):
        print(f"FAIL: tasks fixture not found: {tasks}")
        return 1

    key_var = KEY_ENV.get(provider)
    if not key_var or not os.environ.get(key_var):
        print(f"FAIL: {key_var or 'provider key'} must be set for provider "
              f"'{provider}'.")
        return 1

    with tempfile.TemporaryDirectory() as out_dir:
        cmd = (
            ["docker", "run", "--rm"]
            + shlex.split(run_flags)
            + [
                "-e", f"CAPTION_PROVIDER={provider}",
                "-e", f"{key_var}={os.environ[key_var]}",
                "-v", f"{os.path.abspath(tasks)}:/input/tasks.json:ro",
                "-v", f"{out_dir}:/output",
                image,
            ]
        )
        printable = " ".join(
            shlex.quote("***" if c.startswith(f"{key_var}=") else c) for c in cmd
        )
        print("Running:", printable)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"FAIL: container exceeded {timeout}s timeout")
            return 1

        if proc.returncode != 0:
            print(f"FAIL: container exited {proc.returncode}")
            print("----- stdout -----\n" + proc.stdout[-4000:])
            print("----- stderr -----\n" + proc.stderr[-4000:])
            return 1

        results_path = os.path.join(out_dir, "results.json")
        if not os.path.exists(results_path):
            print("FAIL: container wrote no /output/results.json")
            print("----- stdout -----\n" + proc.stdout[-4000:])
            return 1

        errors = load_and_validate(tasks, results_path)
        if errors:
            print("FAIL: output does not satisfy the contract:")
            for e in errors:
                print("  -", e)
            return 1

    print("PASS e2e: container produced a valid results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
