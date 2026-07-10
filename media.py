"""FrameWise — shared media helpers: download a clip and sample frames from it.

Kept provider-agnostic so both the orchestrator (which downloads the clip) and
the frame-based provider adapters (which sample frames) can reuse them.
"""

import os
import shutil
import subprocess

import requests

NUM_FRAMES = int(os.environ.get("NUM_FRAMES", "12"))
FRAME_LONG_SIDE = int(os.environ.get("FRAME_LONG_SIDE", "512"))


def download_video(url: str, dest_dir: str) -> str:
    """Fetch a clip into `dest_dir`, from an HTTP(S) URL or a local path.

    The demo app passes the path Gradio saved an upload to (no scheme), so a
    local path is copied straight through instead of being requested over
    HTTP — the container's `video_url` inputs are always remote.
    """
    dest_path = os.path.join(dest_dir, "clip.mp4")
    if not url.startswith(("http://", "https://")):
        print(f"Using local file {url}")
        shutil.copyfile(url, dest_path)
        print(f"Copied {os.path.getsize(dest_path) / 1e6:.1f} MB")
        return dest_path

    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"Downloaded {os.path.getsize(dest_path) / 1e6:.1f} MB")
    return dest_path


def probe_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True, text=True,
    )
    try:
        d = float(result.stdout.strip())
        return d if d > 0 else 0.0
    except ValueError:
        return 0.0


def extract_frames(
    video_path: str, out_dir: str, num_frames: int = NUM_FRAMES,
    duration: float = 0.0,
) -> list:
    """Extract `num_frames` interior-sampled frames, downscaled on the long side."""
    os.makedirs(out_dir, exist_ok=True)
    if duration <= 0:
        duration = probe_duration(video_path)
    if duration <= 0:
        duration = 60.0

    # Sample at interior timestamps to avoid black lead-in / trailing frames.
    frame_paths = []
    for i in range(num_frames):
        ts = duration * (i + 0.5) / num_frames
        frame_path = os.path.join(out_dir, f"frame_{i:04d}.jpg")
        subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-ss", f"{ts:.2f}", "-i", video_path,
                "-frames:v", "1",
                "-vf", f"scale='min({FRAME_LONG_SIDE},iw)':-2",
                "-q:v", "3", "-y", frame_path,
            ],
            capture_output=True,
        )
        if os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
            frame_paths.append(frame_path)
    return frame_paths
