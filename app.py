"""Gradio demo for the Track 2 video captioning agent.

Thin UI over the same pipeline the container uses (`providers.get_provider`,
`main.run_tasks`) — no captioning logic lives here. Two tabs:

  * Single video: upload a file or paste a URL, pick styles, caption it.
  * Batch tasks file: upload a tasks.json shaped like sample_tasks.json,
    caption every task, and download a results.json matching the
    container's output contract.

Provider selection is via CAPTION_PROVIDER / <PROVIDER>_API_KEY, exactly as
in the container — there is no key-entry UI, since this app is meant to run
as a shared public demo (e.g. a Hugging Face Space).
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

try:
    _provider = get_provider()
    _provider_error = ""
except SystemExit as e:
    _provider = None
    _provider_error = str(e)


def _check_session_cap(count: int) -> None:
    if count >= MAX_REQUESTS_PER_SESSION:
        raise gr.Error(
            f"This demo session has hit its limit of {MAX_REQUESTS_PER_SESSION} "
            "runs. Reload the page to start a new session."
        )


def caption_single(video_file: str, video_url: str, styles: list, count: int):
    if _provider is None:
        raise gr.Error(f"Demo is not configured: {_provider_error}")
    _check_session_cap(count)

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
    results, failed = run_tasks([task], _provider)
    captions = results[0]["captions"]

    if failed:
        raise gr.Error("The caption provider failed on this clip. Check the logs.")

    body = "\n\n".join(f"**{style}**\n\n{captions.get(style, '')}" for style in styles)
    yield body, count + 1


def caption_batch(tasks_file: str, count: int):
    if _provider is None:
        raise gr.Error(f"Demo is not configured: {_provider_error}")
    _check_session_cap(count)

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

    results, failed = run_tasks(tasks, _provider)

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


with gr.Blocks(title="Track 2 — Video Captioning Agent Demo") as demo:
    gr.Markdown("# Video Captioning Agent — Demo")
    if _provider is None:
        gr.Markdown(f"**Configuration error:** {_provider_error}")

    session_count = gr.State(0)

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
            inputs=[video_file, video_url, styles, session_count],
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
            inputs=[tasks_file, session_count],
            outputs=[batch_table, batch_download, batch_status, session_count],
        )


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860"))
    )
