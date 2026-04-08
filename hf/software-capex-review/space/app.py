from __future__ import annotations

import sys
from pathlib import Path

import gradio as gr

SPACE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SPACE_ROOT.parents[1]
if str(SPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(SPACE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    evaluate_cases,
    evaluate_payloads,
    load_cases,
    load_payloads,
    render_markdown,
)


def _resolve_upload_path(file_obj: object | None) -> str | None:
    if file_obj is None:
        return None
    if isinstance(file_obj, str):
        return file_obj
    path = getattr(file_obj, "path", None) or getattr(file_obj, "name", None)
    return str(path) if path is not None else str(file_obj)


def run_sample() -> str:
    result = evaluate_cases(load_cases(DEFAULT_DATASET_PATH))
    return render_markdown(result)


def run_uploaded(file_path: str | None) -> str:
    if not file_path:
        return run_sample()
    payloads = load_payloads(Path(file_path))
    if payloads and isinstance(payloads[0], dict) and "case_id" in payloads[0] and "events" in payloads[0]:
        result = evaluate_cases(payloads)
    else:
        result = evaluate_payloads(payloads)
    return render_markdown(result)


with gr.Blocks(title="workledger software capex review") as demo:
    gr.Markdown(
        "# workledger software capex review\n"
        "Upload trace events or use the bundled sample to watch raw spans collapse into\n"
        "work units, classifications, and a review queue. The capex example is the wedge,\n"
        "but the point is the traces -> work units -> reports transformation."
    )
    with gr.Row():
        upload = gr.File(label="Upload JSONL or JSON case bundle", file_types=[".jsonl", ".json"])
        sample_button = gr.Button("Run bundled sample")
        refresh_button = gr.Button("Run uploaded file")
    output = gr.Markdown()

    sample_button.click(lambda: run_sample(), inputs=[], outputs=output)
    refresh_button.click(
        lambda file: run_uploaded(_resolve_upload_path(file)),
        inputs=upload,
        outputs=output,
    )


if __name__ == "__main__":
    demo.launch()
