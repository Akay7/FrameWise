"""FrameWise — pluggable external caption providers.

`main.py` depends only on the `CaptionProvider` protocol and `get_provider`,
so swapping between Gemini / OpenAI / Anthropic is an env-var change, not a code
change. Each adapter takes a clip and the requested styles and returns one
caption per style from a single model call.

Environment:
  CAPTION_PROVIDER   gemini | openai | anthropic (default: gemini)
  <PROVIDER>_API_KEY the active provider's key (GEMINI_API_KEY, OPENAI_API_KEY,
                     ANTHROPIC_API_KEY) — read at runtime, never baked in.
  <PROVIDER>_MODEL   optional model override per provider.
  REQUEST_TIMEOUT    per-request timeout in seconds (default: 25, under the 30s
                     per-request budget).
  MAX_RETRIES        retries on transient errors (default: 2).
"""

import base64
import json
import os
import re
import tempfile
import time

from media import NUM_FRAMES, extract_frames

DEFAULT_PROVIDER = "gemini"
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "25"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))

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
# Shared prompt + parsing
# --------------------------------------------------------------------------- #
def build_prompt(styles: list, video_native: bool) -> str:
    frames_phrase = (
        "You are shown a short video clip."
        if video_native
        else "You are shown frames sampled in order from a short video clip."
    )
    lines = [
        "You are an expert video captioner. " + frames_phrase,
        "",
        "First, silently observe the concrete visual facts: the setting, the main "
        "subject(s), what they are doing, notable objects, colors, and any motion "
        "or change over time.",
        "",
        "Then write ONE caption per requested style, in English. Every caption must "
        "faithfully reflect what is actually visible — do not invent details. Each "
        "caption should be a single vivid sentence (max two).",
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


def parse_captions(text: str, styles: list) -> dict:
    """Extract a {style: caption} dict from model output, tolerant of noise."""
    captions = {}
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                captions = {k: str(v).strip() for k, v in data.items()}
        except json.JSONDecodeError:
            pass
    return {s: captions.get(s, "") for s in styles}


def _retry(fn, what: str):
    """Call `fn` with bounded retries + backoff; re-raise on final failure."""
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES:
                delay = 2 ** attempt
                print(f"  {what} failed (attempt {attempt + 1}): {e}; "
                      f"retrying in {delay}s")
                time.sleep(delay)
    raise RuntimeError(f"{what} failed after {MAX_RETRIES + 1} attempts: {last}")


def _b64_frames(clip_path: str, duration: float) -> list:
    """Sample frames from the clip and return their base64-encoded JPEG bytes."""
    with tempfile.TemporaryDirectory() as frame_dir:
        paths = extract_frames(clip_path, frame_dir, NUM_FRAMES, duration)
        if not paths:
            raise RuntimeError("no frames extracted from clip")
        out = []
        for p in paths:
            with open(p, "rb") as f:
                out.append(base64.b64encode(f.read()).decode("ascii"))
        return out


# --------------------------------------------------------------------------- #
# Credentials
# --------------------------------------------------------------------------- #
def _require_key(env_var: str) -> str:
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise SystemExit(
            f"ERROR: {env_var} is not set. The selected caption provider needs "
            f"its API key in the {env_var} environment variable."
        )
    return key


# --------------------------------------------------------------------------- #
# Adapters
# --------------------------------------------------------------------------- #
class GeminiProvider:
    """Native-video provider: upload the clip and caption it in one call."""

    supports_video = True

    def __init__(self, api_key: str = None, **_ignored):
        from google import genai  # noqa: F401  (import-time availability check)

        self._genai = genai
        self._client = genai.Client(api_key=api_key or _require_key("GEMINI_API_KEY"))
        self._model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def caption_clip(self, clip_path: str, duration: float, styles: list) -> dict:
        prompt = build_prompt(styles, video_native=True)

        def _call():
            uploaded = self._client.files.upload(file=clip_path)
            # Wait for the Files API to finish processing the video.
            deadline = time.time() + REQUEST_TIMEOUT
            while getattr(uploaded.state, "name", uploaded.state) == "PROCESSING":
                if time.time() > deadline:
                    raise RuntimeError("Gemini file processing timed out")
                time.sleep(1)
                uploaded = self._client.files.get(name=uploaded.name)
            if getattr(uploaded.state, "name", uploaded.state) == "FAILED":
                raise RuntimeError("Gemini file processing failed")
            resp = self._client.models.generate_content(
                model=self._model,
                contents=[uploaded, prompt],
            )
            return resp.text

        text = _retry(_call, "Gemini request")
        return parse_captions(text, styles)


class OpenAIProvider:
    """Frame-based provider: sample frames and send them as images."""

    supports_video = False

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None,
                 **_ignored):
        from openai import OpenAI

        # base_url lets this adapter target any OpenAI-compatible server,
        # including a local one (Lemonade, vLLM, LM Studio, Ollama). Local
        # servers don't need a real key, so only require one for the cloud API.
        base_url = base_url or os.environ.get("OPENAI_BASE_URL", "").strip() or None
        if api_key:
            resolved_key = api_key
        elif base_url:
            resolved_key = os.environ.get("OPENAI_API_KEY", "").strip() or "local"
        else:
            resolved_key = _require_key("OPENAI_API_KEY")
        self._client = OpenAI(
            api_key=resolved_key, base_url=base_url, timeout=REQUEST_TIMEOUT
        )
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")

    def caption_clip(self, clip_path: str, duration: float, styles: list) -> dict:
        prompt = build_prompt(styles, video_native=False)
        frames = _b64_frames(clip_path, duration)
        content = [{"type": "text", "text": prompt}]
        for b64 in frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        def _call():
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": content}],
            )
            return resp.choices[0].message.content

        text = _retry(_call, "OpenAI request")
        return parse_captions(text, styles)


class AnthropicProvider:
    """Frame-based provider: sample frames and send them as images."""

    supports_video = False

    def __init__(self, api_key: str = None, **_ignored):
        from anthropic import Anthropic

        self._client = Anthropic(
            api_key=api_key or _require_key("ANTHROPIC_API_KEY"),
            timeout=REQUEST_TIMEOUT,
        )
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    def caption_clip(self, clip_path: str, duration: float, styles: list) -> dict:
        prompt = build_prompt(styles, video_native=False)
        frames = _b64_frames(clip_path, duration)
        content = [{"type": "text", "text": prompt}]
        for b64 in frames:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })

        def _call():
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": content}],
            )
            return "".join(
                block.text for block in resp.content
                if getattr(block, "type", None) == "text"
            )

        text = _retry(_call, "Anthropic request")
        return parse_captions(text, styles)


_PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: str = None, api_key: str = None, base_url: str = None,
                  model: str = None):
    """Instantiate the configured provider adapter.

    `api_key`/`base_url`/`model` are optional explicit overrides (used by the
    demo app, where a visitor supplies their own credentials per request);
    when omitted, each adapter falls back to its usual environment variable,
    so the container's `get_provider()` call is unaffected.

    Raises SystemExit on an unknown provider or a missing key, so the run fails
    loudly at startup rather than emitting empty captions.
    """
    name = (name or os.environ.get("CAPTION_PROVIDER") or DEFAULT_PROVIDER).lower()
    if name not in _PROVIDERS:
        supported = ", ".join(sorted(_PROVIDERS))
        raise SystemExit(
            f"ERROR: unknown CAPTION_PROVIDER '{name}'. Supported: {supported}."
        )
    print(f"Caption provider: {name}")
    return _PROVIDERS[name](api_key=api_key, base_url=base_url, model=model)
