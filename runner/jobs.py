"""Filesystem-backed job state used by every Research Starter task."""

from __future__ import annotations

import json
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ALLOWED_STATUSES = {"created", "running", "completed", "failed", "cancelled"}
TASK_LABELS = {
    "paper-guide": "论文导读",
    "research-note": "研究笔记",
    "research-slides": "研究幻灯片",
}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_job_title(task: str, source_paths: Iterable[str]) -> str:
    first = next(iter(source_paths), "未命名素材")
    source_name = Path(first).stem.replace("_", " ").replace("-", " ").strip()
    source_name = " ".join(source_name.split()) or "未命名素材"
    if len(source_name) > 32:
        source_name = source_name[:31] + "…"
    return f"{TASK_LABELS.get(task, '研究任务')}：{source_name}"


@dataclass(frozen=True)
class JobWorkspace:
    root: Path

    @property
    def input(self) -> Path:
        return self.root / "input"

    @property
    def temp(self) -> Path:
        return self.root / "temp"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def state_path(self) -> Path:
        return self.root / "job.json"

    @property
    def log_path(self) -> Path:
        return self.root / "job.log"

    def read(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def update(self, **changes: Any) -> dict[str, Any]:
        state = self.read()
        if "status" in changes and changes["status"] not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported status: {changes['status']}")
        state.update(changes)
        state["updated_at"] = _now()
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)
        return state

    def log(self, message: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{_now()} {message}\n")


def create_job(jobs_root: Path, task: str, sources: Iterable[Path]) -> JobWorkspace:
    job_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
    job = JobWorkspace((jobs_root / job_id).resolve())
    for directory in (job.input, job.temp, job.output):
        directory.mkdir(parents=True, exist_ok=False)

    copied: list[str] = []
    for source in sources:
        source = source.resolve(strict=True)
        destination = job.input / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        copied.append(str(destination))

    state = {
        "job_id": job_id,
        "task": task,
        "status": "created",
        "stage": "created",
        "created_at": _now(),
        "updated_at": _now(),
        "thread_id": None,
        "source_files": copied,
        "title": default_job_title(task, copied),
        "outputs": [],
        "cloud_sync_status": "not_started",
        "cloud_outputs": [],
        "final_response": None,
        "initial_response": None,
        "follow_ups": [],
        "starred": False,
        "error": None,
    }
    job.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    job.log("job created")
    return job
