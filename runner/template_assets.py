"""Persistent analysis assets for reusable PPTX templates."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ANALYSIS_DIRECTORY = ".research-starter-analysis"
PROFILE_JSON = "profile.json"
PROFILE_MARKDOWN = "profile.md"
PROFILE_SCHEMA = 1


def analysis_root(template_library: Path) -> Path:
    return template_library / ANALYSIS_DIRECTORY


def profile_directory(template_library: Path, template: Path) -> Path:
    return analysis_root(template_library) / template.name


def load_profile(template_library: Path, template: Path) -> dict[str, Any] | None:
    directory = profile_directory(template_library, template)
    json_path = directory / PROFILE_JSON
    markdown_path = directory / PROFILE_MARKDOWN
    if not json_path.is_file() or not markdown_path.is_file():
        return None
    try:
        profile = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        profile.get("schema_version") != PROFILE_SCHEMA
        or not isinstance(profile.get("slides"), list)
        or not profile["slides"]
    ):
        return None
    return profile


def require_profile(template_library: Path, template: Path) -> tuple[Path, Path]:
    profile = load_profile(template_library, template)
    if profile is None:
        raise ValueError("该模板尚未完成载入分析；请先执行一次模板载入")
    directory = profile_directory(template_library, template)
    return directory / PROFILE_JSON, directory / PROFILE_MARKDOWN


def validate_generated_profile(directory: Path, template: Path) -> dict[str, Any]:
    json_path = directory / PROFILE_JSON
    markdown_path = directory / PROFILE_MARKDOWN
    if not json_path.is_file() or not markdown_path.is_file():
        raise ValueError("模板载入没有生成 profile.json 和 profile.md")
    profile = json.loads(json_path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != PROFILE_SCHEMA:
        raise ValueError("模板档案 schema_version 不正确")
    slides = profile.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("模板档案缺少逐页分析")
    if profile.get("template_name") != template.name:
        raise ValueError("模板档案中的文件名与当前模板不一致")
    if profile.get("slide_count") != len(slides):
        raise ValueError("模板档案声明的页数与逐页分析数量不一致")
    numbers = [slide.get("slide_number") for slide in slides if isinstance(slide, dict)]
    if numbers != list(range(1, len(slides) + 1)):
        raise ValueError("模板档案的页码存在缺失、重复或顺序错误")
    required = {"slide_number", "visual_role", "suitable_for", "capacity", "objects"}
    for slide in slides:
        if not isinstance(slide, dict) or not required.issubset(slide):
            raise ValueError("模板档案中的逐页字段不完整")
    if not markdown_path.read_text(encoding="utf-8").strip():
        raise ValueError("模板档案说明为空")
    return profile


def install_profile(template_library: Path, template: Path, generated: Path) -> Path:
    validate_generated_profile(generated, template)
    destination = profile_directory(template_library, template)
    temporary = destination.with_name(destination.name + ".installing")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(generated, temporary)
    if destination.exists():
        shutil.rmtree(destination)
    temporary.replace(destination)
    return destination


def copy_profile_to_job(template_library: Path, template: Path, destination: Path) -> Path:
    source_json, source_markdown = require_profile(template_library, template)
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_json, destination / PROFILE_JSON)
    shutil.copy2(source_markdown, destination / PROFILE_MARKDOWN)
    return destination
