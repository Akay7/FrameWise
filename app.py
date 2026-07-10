"""FrameWise — Gradio demo (Track 2 — Video Captioning Agent).

Thin UI over the same pipeline the container uses (`providers.get_provider`,
`main.run_tasks`) — no captioning logic lives here. Two tabs:

  * Single video: upload a file or paste a URL, pick styles, caption it.
  * Batch tasks file: upload a tasks.json shaped like sample_tasks.json,
    caption every task, and download a results.json matching the
    container's output contract.

Each visitor supplies their own provider + API key via the UI (a shared
demo has no server-side key to protect quota/cost on). The key is used only
in-memory for the duration of a request — never logged, stored, or echoed
back. Selecting `openai` also unlocks optional Base URL / Model fields,
mirroring the container's OPENAI_BASE_URL/OPENAI_MODEL overrides, so a
visitor can point the demo at their own OpenAI-compatible server (e.g. a
local Lemonade instance) with no real key required.
"""

import json
import os
import tempfile

import gradio as gr

from main import run_tasks
from providers import ALL_STYLES, get_provider

MAX_VIDEO_MB = int(os.environ.get("DEMO_MAX_VIDEO_MB", "200"))
MAX_BATCH_TASKS = int(os.environ.get("DEMO_MAX_BATCH_TASKS", "10"))
MAX_REQUESTS_PER_SESSION = int(os.environ.get("DEMO_MAX_REQUESTS_PER_SESSION", "20"))

PROVIDERS = ["gemini", "openai", "anthropic"]


def _check_session_cap(count: int) -> None:
    if count >= MAX_REQUESTS_PER_SESSION:
        raise gr.Error(
            f"This demo session has hit its limit of {MAX_REQUESTS_PER_SESSION} "
            "runs (protects the shared free-tier compute this demo runs on). "
            "Reload the page to start a new session."
        )


def _build_provider(provider_name: str, api_key: str, base_url: str, model: str):
    api_key = (api_key or "").strip() or None
    base_url = (base_url or "").strip() or None
    model = (model or "").strip() or None

    if not api_key and not (provider_name == "openai" and base_url):
        raise gr.Error(
            "Enter your API key for the selected provider (or a Base URL, for "
            "an OpenAI-compatible server that doesn't need one)."
        )

    try:
        return get_provider(provider_name, api_key=api_key, base_url=base_url,
                             model=model)
    except SystemExit as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise gr.Error(
            f"Could not initialize the {provider_name} provider — check your "
            f"API key and settings ({e})"
        ) from e


def caption_single(video_file: str, video_url: str, styles: list,
                    provider_name: str, api_key: str, base_url: str, model: str,
                    count: int):
    _check_session_cap(count)
    provider = _build_provider(provider_name, api_key, base_url, model)

    if not styles:
        raise gr.Error("Select at least one caption style.")
    if bool(video_file) == bool(video_url and video_url.strip()):
        raise gr.Error(
            "Provide exactly one of: an uploaded video file, or a video URL."
        )

    if video_file:
        size_mb = os.path.getsize(video_file) / 1e6
        if size_mb > MAX_VIDEO_MB:
            raise gr.Error(
                f"Video is {size_mb:.0f} MB, over the {MAX_VIDEO_MB} MB demo limit."
            )
        source = video_file
    else:
        source = video_url.strip()

    yield "Running caption pipeline…", count

    task = {"task_id": "demo", "video_url": source, "styles": styles}
    results, failed = run_tasks([task], provider)
    captions = results[0]["captions"]

    if failed:
        raise gr.Error(
            "The caption provider failed on this clip — check your API key and "
            "settings."
        )

    body = "\n\n".join(f"**{style}**\n\n{captions.get(style, '')}" for style in styles)
    yield body, count + 1


def caption_batch(tasks_file: str, provider_name: str, api_key: str, base_url: str,
                   model: str, count: int):
    _check_session_cap(count)
    provider = _build_provider(provider_name, api_key, base_url, model)

    if not tasks_file:
        raise gr.Error("Upload a tasks.json file first.")

    try:
        with open(tasks_file) as f:
            tasks = json.load(f)
    except json.JSONDecodeError as e:
        raise gr.Error(f"tasks.json is not valid JSON: {e}") from e

    if not isinstance(tasks, list) or not tasks:
        raise gr.Error("tasks.json must be a non-empty JSON array.")
    if len(tasks) > MAX_BATCH_TASKS:
        raise gr.Error(
            f"tasks.json has {len(tasks)} tasks, over the {MAX_BATCH_TASKS}-task "
            "demo limit."
        )
    for i, task in enumerate(tasks):
        if not isinstance(task, dict) or not task.get("video_url"):
            raise gr.Error(f"tasks[{i}] is missing 'video_url'.")

    yield None, None, "Running caption pipeline…", count

    results, failed = run_tasks(tasks, provider)

    rows = []
    for res in results:
        row = {"task_id": res["task_id"]}
        row.update(res["captions"])
        rows.append(row)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="results_"
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        out_path = f.name

    status = f"Done: {len(results)} task(s), {len(failed)} failed."
    yield rows, out_path, status, count + 1


with gr.Blocks(title="FrameWise — Demo") as demo:
    gr.Markdown(
        "# FrameWise — Demo\n"
        "*Track 2 — Video Captioning Agent*\n\n"
        "Bring your own provider API key — it's used only for your request "
        "and never stored or logged."
    )

    session_count = gr.State(0)

    with gr.Group():
        with gr.Row():
            provider_dd = gr.Dropdown(
                choices=PROVIDERS, value="gemini", label="Caption provider"
            )
            api_key_tb = gr.Textbox(
                label="Your API key", type="password",
                placeholder="Required (optional if a Base URL is set below)",
            )
        with gr.Row(visible=False) as openai_extra:
            base_url_tb = gr.Textbox(
                label="OpenAI-compatible Base URL (optional)",
                placeholder="e.g. http://localhost:8000/api/v1 for a local server",
            )
            model_tb = gr.Textbox(
                label="Model (optional)", placeholder="defaults to gpt-4o"
            )
        provider_dd.change(
            lambda p: gr.update(visible=p == "openai"),
            inputs=provider_dd, outputs=openai_extra,
        )

    with gr.Tab("Single video"):
        with gr.Row():
            video_file = gr.Video(label="Upload a video", sources=["upload"])
            video_url = gr.Textbox(label="...or a video URL")
        styles = gr.CheckboxGroup(
            choices=ALL_STYLES, value=ALL_STYLES, label="Caption styles"
        )
        run_single = gr.Button("Caption", variant="primary")
        single_output = gr.Markdown()
        run_single.click(
            caption_single,
            inputs=[video_file, video_url, styles, provider_dd, api_key_tb,
                     base_url_tb, model_tb, session_count],
            outputs=[single_output, session_count],
        )

    with gr.Tab("Batch tasks file"):
        gr.Markdown(
            f"Upload a JSON array shaped like `sample_tasks.json` "
            f"(`task_id`, `video_url`, `styles`), up to {MAX_BATCH_TASKS} tasks."
        )
        tasks_file = gr.File(label="tasks.json", file_types=[".json"])
        run_batch = gr.Button("Run batch", variant="primary")
        batch_status = gr.Markdown()
        batch_table = gr.Dataframe(label="Results", wrap=True)
        batch_download = gr.File(label="Download results.json")
        run_batch.click(
            caption_batch,
            inputs=[tasks_file, provider_dd, api_key_tb, base_url_tb, model_tb,
                     session_count],
            outputs=[batch_table, batch_download, batch_status, session_count],
        )


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860"))
    )
