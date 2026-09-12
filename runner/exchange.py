"""Low-frequency iCloud copy-in/copy-out boundary for Phase 2."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Iterable

from .config import Settings
from .jobs import JobWorkspace


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (FileNotFoundError, ValueError):
        return False


def validate_icloud_sources(task: str, sources: Iterable[Path], settings: Settings) -> list[Path]:
    if settings.icloud_inbox_root is None:
        raise ValueError("iCloud material input is not configured")
    task_root = (settings.icloud_inbox_root / task).resolve(strict=True)
    validated: list[Path] = []
    for source in sources:
        source = source.resolve(strict=True)
        if not _inside(source, task_root):
            raise ValueError(f"iCloud source is outside {task_root}: {source}")
        files = [source] if source.is_file() else [path for path in source.rglob("*") if path.is_file()]
        if not files:
            raise ValueError(f"iCloud source contains no readable files: {source}")
        for file_path in files:
            expected = file_path.stat().st_size
            with file_path.open("rb") as handle:
                while handle.read(1024 * 1024):
                    pass
            if file_path.stat().st_size != expected:
                raise OSError(f"iCloud source changed while being read: {file_path}")
        validated.append(source)
    return validated


def verify_local_outputs(task: str, job: JobWorkspace) -> list[Path]:
    outputs = [path for path in job.output.rglob("*") if path.is_file()]
    if task in {"paper-guide", "research-slides"} and not outputs:
        raise FileNotFoundError(f"{task} created no local output")
    for output in outputs:
        if output.stat().st_size <= 0:
            raise ValueError(f"Local output is empty: {output}")
        if output.suffix.lower() == ".pptx":
            if not zipfile.is_zipfile(output):
                raise ValueError(f"PPTX is not a readable OOXML ZIP: {output}")
            with zipfile.ZipFile(output) as archive:
                if "ppt/presentation.xml" not in archive.namelist():
                    raise ValueError(f"PPTX lacks ppt/presentation.xml: {output}")
    return outputs


def publish_outputs(task: str, job: JobWorkspace, settings: Settings) -> list[Path]:
    if settings.icloud_output_root is None:
        raise ValueError("iCloud output is not configured")
    local_outputs = verify_local_outputs(task, job)
    destination_root = settings.icloud_output_root / task
    destination_root.mkdir(parents=True, exist_ok=True)
    published: list[Path] = []
    for source in local_outputs:
        relative = source.relative_to(job.output)
        destination = destination_root / f"{job.root.name}-{relative.name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        uploading = destination.with_name(destination.name + ".uploading")
        shutil.copy2(source, uploading)
        if uploading.stat().st_size != source.stat().st_size:
            raise OSError(f"iCloud copy size mismatch: {source} -> {uploading}")
        uploading.replace(destination)
        published.append(destination)
    return published
