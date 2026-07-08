"""Track 2 — Video Captioning Agent.

Reads /input/tasks.json, generates a caption per requested style for every clip
using a single local video-native VLM (Qwen2.5-VL), and writes
/output/results.json.

Design:
  * Load the VLM once at startup (global), reused across all clips.
  * One VLM call per clip: pass evenly-sampled frames and ask for ALL requested
    styles at once as strict JSON. The vision encoding — the expensive part — is
    shared across styles, and every caption is grounded in the same observed
    facts, keeping accuracy consistent and staying well within the 10-min budget.
"""

import json
import os
import re
import subprocess
import tempfile
import time
import traceback

import requests

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct")
NUM_FRAMES = int(os.environ.get("NUM_FRAMES", "12"))
FRAME_LONG_SIDE = int(os.environ.get("FRAME_LONG_SIDE", "512"))
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "640"))
# "single" = one call emits all styles. "two_pass" = a factual grounding call
# feeds a dedicated styling call (better accuracy/style separation, ~2x calls).
CAPTION_MODE = os.environ.get("CAPTION_MODE", "single").lower()
GROUNDING_MAX_TOKENS = int(os.environ.get("GROUNDING_MAX_TOKENS", "256"))

ALL_STYLES = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]

STYLE_GUIDE = {
    "formal": (
        "Professional, objective, factual. Neutral tone, precise, no humor or "
        "opinion."
    ),
    "sarcastic": (
        "Dry, ironic, lightly mocking. Witty and wry but not mean-spirited; still "
        "describes what actually happens."
    ),
    "humorous_tech": (
        "Funny, with technology or programming references. Compare what is on "
        "screen to code, bugs, software, or IT culture. Clever and tech-fluent."
    ),
    "humorous_non_tech": (
        "Funny with everyday, relatable humor. Observational comedy and real-world "
        "analogies. Absolutely no technical or programming jargon."
    ),
}


# --------------------------------------------------------------------------- #
# Model (loaded once, lazily, and cached globally)
# --------------------------------------------------------------------------- #
_MODEL = None
_PROCESSOR = None


def load_model():
    """Load Qwen2.5-VL once and cache it for reuse across clips."""
    global _MODEL, _PROCESSOR
    if _MODEL is not None:
        return _MODEL, _PROCESSOR

    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    print(f"Loading VLM: {MODEL_ID}")
    t0 = time.time()
    _MODEL = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map="auto",
    )
    _MODEL.eval()
    # Cap the visual token budget so long/high-res clips stay fast and bounded.
    _PROCESSOR = AutoProcessor.from_pretrained(
        MODEL_ID,
        min_pixels=256 * 28 * 28,
        max_pixels=768 * 28 * 28,
    )
    print(f"Model ready in {time.time() - t0:.1f}s (device={_MODEL.device})")
    return _MODEL, _PROCESSOR


# --------------------------------------------------------------------------- #
# Video handling
# --------------------------------------------------------------------------- #
def download_video(url: str, dest_dir: str) -> str:
    dest_path = os.path.join(dest_dir, "clip.mp4")
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


def extract_frames(video_path: str, out_dir: str, num_frames: int) -> list:
    """Extract `num_frames` evenly-spaced frames, downscaled on the long side."""
    os.makedirs(out_dir, exist_ok=True)
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


# --------------------------------------------------------------------------- #
# Captioning
# --------------------------------------------------------------------------- #
def build_prompt(styles: list) -> str:
    lines = [
        "You are an expert video captioner. You are shown frames sampled in "
        "order from a short video clip.",
        "",
        "First, silently observe the concrete visual facts: the setting, the main "
        "subject(s), what they are doing, notable objects, colors, and any motion "
        "or change across the frames.",
        "",
        "Then write ONE caption per requested style. Every caption must faithfully "
        "reflect what is actually visible in the clip — do not invent details. "
        "Each caption should be a single vivid sentence (max two).",
        "",
        "Requested styles:",
    ]
    for s in styles:
        lines.append(f'  - "{s}": {STYLE_GUIDE.get(s, s)}')
    lines += [
        "",
        "Respond with ONLY a JSON object mapping each requested style name to its "
        "caption string. No markdown, no commentary, no extra keys. Example shape:",
        "{" + ", ".join(f'"{s}": "..."' for s in styles) + "}",
    ]
    return "\n".join(lines)


def _parse_captions(text: str, styles: list) -> dict:
    """Extract a {style: caption} dict from model output, tolerant of noise."""
    captions = {}
    # Grab the outermost JSON object if present.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                captions = {k: str(v).strip() for k, v in data.items()}
        except json.JSONDecodeError:
            pass
    # Ensure every requested style is present.
    return {s: captions.get(s, "") for s in styles}


def build_grounding_prompt() -> str:
    return (
        "You are shown frames sampled in order from a short video clip. Describe, "
        "factually and concretely, exactly what the clip depicts: the setting, the "
        "main subject(s), what they are doing, notable objects, colors, and any "
        "motion or change across the frames. Be specific and accurate; do not "
        "guess or embellish. Write 2-4 plain sentences, no styling."
    )


def build_style_prompt(styles: list, grounding: str) -> str:
    lines = [
        "Here is a factual description of a short video clip:",
        f'"""{grounding}"""',
        "",
        "You are also shown the clip's frames. Write ONE caption per requested "
        "style. Every caption must stay faithful to the description and the frames "
        "— do not invent details. Each caption is a single vivid sentence (max two).",
        "",
        "Requested styles:",
    ]
    for s in styles:
        lines.append(f'  - "{s}": {STYLE_GUIDE.get(s, s)}')
    lines += [
        "",
        "Respond with ONLY a JSON object mapping each requested style name to its "
        "caption string. No markdown, no commentary, no extra keys. Example shape:",
        "{" + ", ".join(f'"{s}": "..."' for s in styles) + "}",
    ]
    return "\n".join(lines)


def _generate(frame_paths, prompt, model, processor, sample=False, max_tokens=None):
    """Run one VLM forward pass over the frames + prompt, return decoded text."""
    from qwen_vl_utils import process_vision_info
    import torch

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": frame_paths, "fps": 1.0},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(model.device)

    gen_kwargs = {"max_new_tokens": max_tokens or MAX_NEW_TOKENS}
    if sample:
        gen_kwargs.update(do_sample=True, temperature=0.7, top_p=0.9)
    else:
        gen_kwargs.update(do_sample=False)

    with torch.no_grad():
        generated = model.generate(**inputs, **gen_kwargs)
    trimmed = generated[0][inputs.input_ids.shape[1]:]
    return processor.decode(trimmed, skip_special_tokens=True).strip()


def caption_clip(frame_paths: list, styles: list) -> dict:
    model, processor = load_model()

    if CAPTION_MODE == "two_pass":
        grounding = _generate(
            frame_paths, build_grounding_prompt(), model, processor,
            sample=False, max_tokens=GROUNDING_MAX_TOKENS,
        )
        print(f"  Grounding: {grounding[:300]}")
        style_prompt = build_style_prompt(styles, grounding)
    else:
        style_prompt = build_prompt(styles)

    out = _generate(frame_paths, style_prompt, model, processor, sample=False)
    print(f"  Raw output: {out[:300]}")
    captions = _parse_captions(out, styles)

    # Retry once (sampled) for any style that came back empty.
    missing = [s for s in styles if not captions[s]]
    if missing:
        print(f"  Retrying missing styles: {missing}")
        retry_prompt = (
            build_style_prompt(missing, grounding)
            if CAPTION_MODE == "two_pass"
            else build_prompt(missing)
        )
        retry_out = _generate(frame_paths, retry_prompt, model, processor, sample=True)
        captions.update(_parse_captions(retry_out, missing))
    return captions


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def process_task(task: dict) -> dict:
    task_id = task.get("task_id", "unknown")
    video_url = task["video_url"]
    styles = task.get("styles") or ALL_STYLES

    print(f"\n{'=' * 60}\nTask {task_id} | styles={styles}\n{'=' * 60}")
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        video_path = download_video(video_url, tmp)
        frames = extract_frames(video_path, os.path.join(tmp, "frames"), NUM_FRAMES)
        print(f"Extracted {len(frames)} frames")
        if not frames:
            raise RuntimeError("no frames extracted")
        captions = caption_clip(frames, styles)

    print(f"Task {task_id} done in {time.time() - t0:.1f}s")
    for s in styles:
        print(f"  [{s}] {captions[s][:120]}")
    return {"task_id": task_id, "captions": captions}


def main():
    start = time.time()
    print(f"Loading tasks from {INPUT_PATH}")
    with open(INPUT_PATH) as f:
        tasks = json.load(f)

    # Warm the model before the loop so its cost isn't attributed to clip 1.
    try:
        load_model()
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: model preload failed: {e}")
        traceback.print_exc()

    results = []
    for task in tasks:
        styles = task.get("styles") or ALL_STYLES
        try:
            results.append(process_task(task))
        except Exception as e:  # noqa: BLE001
            print(f"ERROR on task {task.get('task_id', 'unknown')}: {e}")
            traceback.print_exc()
            results.append(
                {
                    "task_id": task.get("task_id", "unknown"),
                    "captions": {s: "" for s in styles},
                }
            )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(results)} results to {OUTPUT_PATH} "
          f"({time.time() - start:.1f}s total)")

    # Self-check the output against the contract. Warn only — a partial result
    # still scores better than deleting valid output.
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


if __name__ == "__main__":
    main()
