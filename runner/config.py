"""Local, path-safe configuration for Research Starter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    local_jobs: Path
    local_fallback_output: Path
    icloud_inbox_root: Path | None
    icloud_output_root: Path | None
    codex_home: Path
    obsidian_vault: Path | None
    obsidian_write_root: Path | None
    local_obsidian_vault: Path
    obsidian_exe: Path | None

    @property
    def skills_root(self) -> Path:
        return self.project_root / "skills"

    @property
    def python_exe(self) -> Path:
        return self.project_root / "runtime" / "python" / "python.exe"

    @property
    def node_exe(self) -> Path:
        return self.project_root / "runtime" / "node" / "node.exe"

    @property
    def docling_exe(self) -> Path:
        return self.project_root / "Run Docling.cmd"


def _resolve(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _optional(root: Path, value: object) -> Path | None:
    return _resolve(root, value.strip()) if isinstance(value, str) and value.strip() else None


def load_settings(path: Path | None = None) -> Settings:
    requested = (path or Path("config.local.json")).resolve()
    config_path = requested if requested.is_file() else requested.with_name("config.example.json")
    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    config_dir = config_path.parent
    project_root = _resolve(config_dir, data.get("project_root", "."))
    settings = Settings(
        project_root=project_root,
        local_jobs=_resolve(project_root, data["local_jobs"]),
        local_fallback_output=_resolve(project_root, data["local_fallback_output"]),
        icloud_inbox_root=_optional(project_root, data.get("icloud_inbox_root")),
        icloud_output_root=_optional(project_root, data.get("icloud_output_root")),
        codex_home=_resolve(project_root, data.get("codex_home") or str(Path.home() / ".codex")),
        obsidian_vault=_optional(project_root, data.get("obsidian_vault")),
        obsidian_write_root=_optional(project_root, data.get("obsidian_write_root")),
        local_obsidian_vault=_resolve(project_root, data.get("local_obsidian_vault", ".runtime/obsidian-local-vault")),
        obsidian_exe=_optional(project_root, data.get("obsidian_exe")),
    )
    for directory in (settings.local_jobs, settings.local_fallback_output, settings.local_obsidian_vault):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
