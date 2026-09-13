"""Seed release-safe completed examples into a fresh local project library."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings

EXAMPLES = {
    "example-paper-guide": ("paper-guide", "示例：偏振研究论文导读"),
    "example-research-note": ("research-note", "示例：偏振实验研究笔记"),
    "example-research-slides": ("research-slides", "示例：温度扫描研究幻灯片"),
}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def seed_completed_examples(settings: Settings) -> list[str]:
    """Create missing examples only; never modify an existing job directory."""
    marker = settings.project_root / ".runtime" / "examples-seeded-v2"
    if marker.exists():
        return []
    created: list[str] = []
    for job_id, (task, title) in EXAMPLES.items():
        root = settings.local_jobs / job_id
        if root.exists():
            state_path = root / "job.json"
            if task == "research-slides" and state_path.is_file():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                sample_deck = settings.project_root / "Output" / task / "public-sample" / "temperature-scan-example.pptx"
                if state.get("is_example") and sample_deck.is_file() and not state.get("outputs"):
                    destination = root / "output" / sample_deck.name
                    shutil.copy2(sample_deck, destination)
                    state.update(outputs=[str(destination)], latest_pptx=str(destination))
                    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            continue
        input_dir, output_dir, temp_dir = root / "input", root / "output", root / "temp"
        input_dir.mkdir(parents=True)
        output_dir.mkdir()
        temp_dir.mkdir()
        source = settings.project_root / "Inbox" / task / "public-sample"
        published = settings.project_root / "Output" / task / "public-sample"
        if source.is_dir():
            shutil.copytree(source, input_dir / "public-sample")
        if published.is_dir():
            shutil.copytree(published, output_dir / "public-sample")
        stamp = _now()
        state = {
            "job_id": job_id, "task": task, "status": "completed", "stage": "completed",
            "created_at": stamp, "updated_at": stamp, "thread_id": None,
            "source_files": [str(input_dir / "public-sample")], "title": title,
            "outputs": [], "cloud_sync_status": "not_applicable", "cloud_outputs": [],
            "final_response": None, "initial_response": None, "follow_ups": [],
            "starred": True, "error": None, "language": "zh", "model_provider": "example",
            "model": "示例内容（不消耗额度）", "reasoning_effort": "not applicable", "is_example": True,
        }
        if task == "paper-guide":
            state["initial_response"] = (published / "README.md").read_text(encoding="utf-8")
            state["final_response"] = state["initial_response"]
        elif task == "research-note":
            note = (published / "example-note.md").read_text(encoding="utf-8")
            state.update(final_response=note, initial_response=note, note_preview=note, note_target="示例/偏振实验.md")
        else:
            response = (published / "README.md").read_text(encoding="utf-8")
            sample_deck = published / "temperature-scan-example.pptx"
            destination = output_dir / "public-sample" / sample_deck.name
            outputs = [str(destination)] if destination.is_file() else []
            state.update(final_response=response, initial_response=response, outputs=outputs,
                         latest_pptx=outputs[0] if outputs else None)
        (root / "job.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "job.log").write_text(f"{stamp} bundled example seeded\n", encoding="utf-8")
        created.append(job_id)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(_now(), encoding="utf-8")
    return created
