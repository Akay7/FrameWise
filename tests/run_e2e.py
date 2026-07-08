"""End-to-end container test: run the built image and validate its output.

Requires Docker and (for the real pipeline) an AMD ROCm GPU plus network access
to download the fixture clip. Guarded so it is skipped unless explicitly opted
into with RUN_E2E=1.

Environment:
  RUN_E2E=1            enable the test (otherwise it skips and exits 0)
  IMAGE=<tag>          image to run (default: video-caption:latest)
  E2E_TASKS=<path>     tasks fixture to mount (default: tests/fixtures/tasks.json)
  DOCKER_GPU_FLAGS     extra `docker run` flags for GPU access
                       (default: --device=/dev/kfd --device=/dev/dri
                        --security-opt seccomp=unconfined --group-add video)
  E2E_TIMEOUT=<secs>   max seconds for the container run (default: 600)

Usage:
  RUN_E2E=1 IMAGE=ghcr.io/you/video-caption:latest python tests/run_e2e.py
"""

import os
import shlex
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from validation import load_and_validate  # noqa: E402

DEFAULT_GPU_FLAGS = (
    "--device=/dev/kfd --device=/dev/dri "
    "--security-opt seccomp=unconfined --group-add video"
)


def main() -> int:
    if os.environ.get("RUN_E2E") != "1":
        print("SKIP e2e: set RUN_E2E=1 to run the container test.")
        return 0

    image = os.environ.get("IMAGE", "video-caption:latest")
    tasks = os.environ.get(
        "E2E_TASKS", os.path.join(REPO_ROOT, "tests", "fixtures", "tasks.json")
    )
    gpu_flags = os.environ.get("DOCKER_GPU_FLAGS", DEFAULT_GPU_FLAGS)
    timeout = int(os.environ.get("E2E_TIMEOUT", "600"))

    if not os.path.exists(tasks):
        print(f"FAIL: tasks fixture not found: {tasks}")
        return 1

    with tempfile.TemporaryDirectory() as out_dir:
        cmd = (
            ["docker", "run", "--rm"]
            + shlex.split(gpu_flags)
            + [
                "-v", f"{os.path.abspath(tasks)}:/input/tasks.json:ro",
                "-v", f"{out_dir}:/output",
                image,
            ]
        )
        print("Running:", " ".join(shlex.quote(c) for c in cmd))
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
