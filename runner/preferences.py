"""Validated local preferences; saving paths never moves existing data."""
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import shutil

from .config import Settings, _resolve

PATH_LABELS = {
    "base_python": "基础 Python（仅用于首次创建项目 .venv）",
    "node_exe": "Node.js 可执行文件（首次安装项目依赖）",
    "npm_cmd": "npm 命令文件（首次安装项目依赖）",
    "local_jobs": "本地项目记录目录",
    "local_fallback_output": "本地备用输出目录",
    "icloud_inbox_root": "iCloud 素材入口（可选）",
    "icloud_output_root": "iCloud 成品出口（可选）",
    "codex_home": "Codex 账户与会话目录",
    "obsidian_vault": "云端 Obsidian Vault 根目录（可选）",
    "obsidian_write_root": "云端 Obsidian 笔记目录（可选）",
    "local_obsidian_vault": "项目本地 Obsidian Vault",
    "obsidian_exe": "Obsidian 可执行文件",
}
OPTIONAL_PATHS = {"icloud_inbox_root", "icloud_output_root", "obsidian_vault", "obsidian_write_root"}
VERSION = "1.0.0-internal.3"


def app_info(root: Path) -> dict:
    return {"version": VERSION, "author": "Ding Ronghao与CodeX", "github_url": ""}


def save_preferences(current: Settings, values: dict) -> Settings:
    if "author" in values or "github_url" in values:
        raise ValueError("制作者和 GitHub 地址属于软件发布信息，不能通过 Settings 修改")
    paths = {}
    for key in PATH_LABELS:
        current_value = getattr(current, key)
        raw = values.get(key, "" if current_value is None else str(current_value))
        if not isinstance(raw, str):
            raise ValueError(f"{PATH_LABELS[key]}格式不正确")
        if key in OPTIONAL_PATHS and not raw.strip():
            paths[key] = None
            continue
        if not raw.strip():
            raise ValueError(f"{PATH_LABELS[key]}不能为空")
        path = _resolve(current.project_root, raw.strip())
        if key in {"base_python", "node_exe", "obsidian_exe"}:
            if not path.is_file() or path.suffix.lower() != ".exe":
                raise ValueError(f"{PATH_LABELS[key]}必须是已有的 .exe 文件")
        elif key == "npm_cmd":
            if not path.is_file() or path.suffix.lower() not in {".cmd", ".exe"}:
                raise ValueError(f"{PATH_LABELS[key]}必须是已有的 npm.cmd 或可执行文件")
        elif not path.is_dir():
            raise ValueError(f"{PATH_LABELS[key]}必须是已有文件夹：{path}")
        paths[key] = path
    for key in ("local_jobs", "local_fallback_output", "local_obsidian_vault"):
        if not paths[key].is_relative_to(current.project_root) or paths[key] == current.project_root:
            raise ValueError("本地工作目录必须位于当前项目内的子文件夹")
    if (paths["obsidian_vault"] is None) != (paths["obsidian_write_root"] is None):
        raise ValueError("云端 Obsidian Vault 与笔记目录必须同时填写或同时留空")
    if paths["obsidian_vault"] is not None:
        if paths["obsidian_write_root"] == paths["obsidian_vault"] or not paths["obsidian_write_root"].is_relative_to(paths["obsidian_vault"]):
            raise ValueError("笔记写入目录必须是 Vault 内的子文件夹")
    for key in ("icloud_inbox_root", "icloud_output_root", "local_jobs", "codex_home"):
        if paths[key] is not None and paths["obsidian_vault"] is not None and paths[key].is_relative_to(paths["obsidian_vault"]):
            raise ValueError(f"{PATH_LABELS[key]}不能放在 Obsidian Vault 内")
    if paths["obsidian_vault"] is not None and paths["local_obsidian_vault"].is_relative_to(paths["obsidian_vault"]):
        raise ValueError("项目本地 Obsidian Vault 不能位于云端 Vault 内")
    config_path = current.project_root / "config.local.json"
    original = json.loads(config_path.read_text(encoding="utf-8-sig"))
    backup = current.project_root / ".runtime" / "config-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    shutil.copy2(config_path, backup / config_path.name)
    project_relative = {"local_jobs", "local_fallback_output", "local_obsidian_vault"}
    original.update({
        key: "" if path is None else (
            path.relative_to(current.project_root).as_posix() if key in project_relative else str(path)
        )
        for key, path in paths.items()
    })
    temporary = config_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(config_path)
    return replace(current, **paths)
