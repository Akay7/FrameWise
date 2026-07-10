"""FrameWise — shared media helpers: download a clip and sample frames from it.

Kept provider-agnostic so both the orchestrator (which downloads the clip) and
the frame-based provider adapters (which sample frames) can reuse them.
"""

import glob
import logging
import os
import shutil
import subprocess

import requests

logger = logging.getLogger(__name__)

# Rate-based sampling (one frame every FRAME_INTERVAL_SECONDS) rather than a
# fixed frame count: shorter clips cost less to process/transmit, and
# MAX_FRAMES caps a pathologically long clip from ballooning memory/payload
# size on a constrained host.
FRAME_INTERVAL_SECONDS = float(os.environ.get("FRAME_INTERVAL_SECONDS", "4"))
FRAME_LONG_SIDE = int(os.environ.get("FRAME_LONG_SIDE", "512"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "30"))


def download_video(url: str, dest_dir: str) -> str:
    """Fetch a clip into `dest_dir`, from an HTTP(S) URL or a local path.

    The demo app passes the path Gradio saved an upload to (no scheme), so a
    local path is copied straight through instead of being requested over
    HTTP — the container's `video_url` inputs are always remote.
    """
    dest_path = os.path.join(dest_dir, "clip.mp4")
    if not url.startswith(("http://", "https://")):
        logger.info("Using local file %s", url)
        shutil.copyfile(url, dest_path)
        logger.info("Copied %.1f MB", os.path.getsize(dest_path) / 1e6)
        return dest_path

    logger.info("Downloading %s", url)
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    logger.info("Downloaded %.1f MB", os.path.getsize(dest_path) / 1e6)
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
    video_path: str, out_dir: str,
    interval_seconds: float = FRAME_INTERVAL_SECONDS, max_frames: int = MAX_FRAMES,
) -> list:
    """Extract one frame every `interval_seconds`, downscaled on the long
    side, in a single ffmpeg pass (cheaper than one subprocess per frame),
    capped at `max_frames` total.
    """
    os.makedirs(out_dir, exist_ok=True)
    fps = 1.0 / interval_seconds
    pattern = os.path.join(out_dir, "frame_%04d.jpg")
    logger.info("Extracting frames (every %ss, long side %spx, max %s)...",
                interval_seconds, FRAME_LONG_SIDE, max_frames)
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-i", video_path,
            "-vf", f"fps={fps},scale='min({FRAME_LONG_SIDE},iw)':-2",
            "-frames:v", str(max_frames),
            "-q:v", "3", "-y", pattern,
        ],
        capture_output=True,
    )
    frame_paths = sorted(glob.glob(os.path.join(out_dir, "frame_*.jpg")))
    frame_paths = [p for p in frame_paths if os.path.getsize(p) > 0]
    logger.info("Extracted %d frame(s)", len(frame_paths))
    return frame_paths
