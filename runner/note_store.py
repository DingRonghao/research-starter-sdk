"""Mechanical local-first storage and one-shot cloud publication for Research Note."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from .config import Settings
from .jobs import JobWorkspace

ATTACHMENT_SUFFIXES = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".pdf", ".png", ".svg", ".webp"}
TARGET_PATTERN = re.compile(r"<research-note-target>\s*([^<]+?)\s*</research-note-target>", re.I)
MODE_PATTERN = re.compile(r"<research-note-mode>\s*(create|append)\s*</research-note-mode>", re.I)
MARKDOWN_PATTERN = re.compile(r"```(?:markdown|md)\s*\n([\s\S]*?)```", re.I)
LEGACY_TARGET_PATTERN = re.compile(r"Target path:\s*`([^`]+\.md)`", re.I)


def cloud_record(settings: Settings) -> Path:
    if settings.obsidian_write_root is None:
        raise ValueError("Cloud Obsidian is not configured")
    return settings.obsidian_write_root


def note_root_relative(settings: Settings) -> PurePosixPath:
    """Return the configured note root inside either Vault, without a user-specific name."""
    if settings.obsidian_write_root is None:
        return PurePosixPath("Notes")
    if settings.obsidian_vault is None:
        raise ValueError("Cloud Obsidian Vault root is not configured")
    relative = settings.obsidian_write_root.resolve().relative_to(settings.obsidian_vault.resolve())
    return PurePosixPath(relative.as_posix())


def local_record(settings: Settings) -> Path:
    return settings.local_obsidian_vault / Path(note_root_relative(settings).as_posix())


def initialize_local_vault(settings: Settings) -> None:
    local_root = settings.local_obsidian_vault.resolve()
    if not local_root.is_relative_to(settings.project_root.resolve()) or local_root == settings.project_root.resolve():
        raise ValueError("Local Obsidian Vault must be a project subdirectory")
    remote = cloud_record(settings).resolve(strict=True) if settings.obsidian_write_root is not None else None
    if remote is not None:
        if settings.obsidian_vault is None:
            raise ValueError("Cloud Obsidian Vault root is not configured")
        remote.relative_to(settings.obsidian_vault.resolve(strict=True))
    marker = local_root / ".research-starter-vault.json"
    local_root.mkdir(parents=True, exist_ok=True)
    (local_root / ".obsidian").mkdir(exist_ok=True)
    destination = local_record(settings)
    if not marker.exists():
        if destination.exists() and any(destination.iterdir()):
            raise ValueError("Local Vault contains data but has no Research Starter initialization marker")
        if remote is not None:
            shutil.copytree(remote, destination, dirs_exist_ok=True)
        else:
            destination.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"cloud_record": str(remote) if remote else None}, ensure_ascii=False, indent=2), encoding="utf-8")
    elif remote is not None and json.loads(marker.read_text(encoding="utf-8")).get("cloud_record") != str(remote):
        raise ValueError("Local Vault is linked to a different cloud Record directory")
    elif remote is not None:
        unpublished = []
        if settings.local_jobs.is_dir():
            for state_path in settings.local_jobs.glob("*/job.json"):
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    if state.get("task") == "research-note" and state.get("note_local_saved") and not state.get("note_cloud_published"):
                        unpublished.append(state.get("job_id", state_path.parent.name))
                except (OSError, json.JSONDecodeError):
                    continue
        if unpublished:
            raise RuntimeError("Local Vault has unpublished Research Note jobs: " + ", ".join(unpublished))
        shutil.copytree(remote, destination, dirs_exist_ok=True)


def parse_preview(response: str, settings: Settings) -> tuple[str, str, str]:
    target_match = TARGET_PATTERN.search(response) or LEGACY_TARGET_PATTERN.search(response)
    markdown_match = MARKDOWN_PATTERN.search(response)
    if not target_match or not markdown_match:
        raise ValueError("Research Note preview is missing the required target or complete Markdown block")
    target = target_match.group(1).replace("\\", "/").strip().lstrip("/")
    path = PurePosixPath(target)
    parts = path.parts
    if ".." in parts or not parts or path.suffix.lower() != ".md":
        raise ValueError("Research Note target is not a safe Markdown path")
    root = note_root_relative(settings)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Research Note target must be under {root.as_posix()}/") from exc
    mode_match = MODE_PATTERN.search(response)
    mode = mode_match.group(1).lower() if mode_match else ("append" if "Append this Markdown" in response else "create")
    return path.as_posix(), mode, markdown_match.group(1).strip()


def independent_target(target: str, language: str, settings: Settings) -> str:
    """Return a collision-free target; a new job never appends to an existing note."""
    relative = PurePosixPath(target)
    destination = settings.local_obsidian_vault / Path(relative.as_posix())
    if not destination.exists():
        return relative.as_posix()
    suffix = {"zh": "zh", "ja": "ja", "en": "en"}.get(language, "note")
    stem = relative.stem
    parent = relative.parent
    candidate_stem = stem if stem.lower().endswith(f"-{suffix}") else f"{stem}-{suffix}"
    index = 1
    while True:
        numbered = candidate_stem if index == 1 else f"{candidate_stem}-{index}"
        candidate = parent / f"{numbered}.md"
        if not (settings.local_obsidian_vault / Path(candidate.as_posix())).exists():
            return candidate.as_posix()
        index += 1


def _hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _attachment_mappings(job: JobWorkspace, settings: Settings) -> list[tuple[str, str, Path]]:
    mappings = []
    prefix = note_root_relative(settings) / "_attachments" / "Research-Starter" / job.root.name
    for source in sorted(job.input.rglob("*")):
        if source.is_file() and source.suffix.lower() in ATTACHMENT_SUFFIXES:
            input_relative = source.relative_to(job.input).as_posix()
            vault_relative = (prefix / PurePosixPath(input_relative)).as_posix()
            mappings.append((input_relative, vault_relative, source))
    return mappings


def save_local(job: JobWorkspace, settings: Settings) -> dict:
    initialize_local_vault(settings)
    state = job.read()
    target_relative = state.get("note_target")
    mode = state.get("note_mode")
    preview = state.get("note_preview")
    if not target_relative or mode not in {"create", "append"} or not isinstance(preview, str):
        raise ValueError("The reviewed preview has no validated local target")
    target_relative = independent_target(target_relative, state.get("language", "zh"), settings)
    mode = "create"
    target = (settings.local_obsidian_vault / Path(target_relative)).resolve()
    target.relative_to(local_record(settings).resolve(strict=True))
    cloud_target = None
    if settings.obsidian_write_root is not None:
        root_relative = Path(note_root_relative(settings).as_posix())
        cloud_target = (cloud_record(settings) / Path(target_relative).relative_to(root_relative)).resolve()
        cloud_target.relative_to(cloud_record(settings).resolve(strict=True))
    mappings = _attachment_mappings(job, settings)
    saved_markdown = preview
    copied = []
    for input_path, vault_path, source in mappings:
        destination = (settings.local_obsidian_vault / Path(vault_path)).resolve()
        destination.relative_to(local_record(settings).resolve(strict=True))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".writing")
        shutil.copy2(source, temporary)
        if _hash(temporary) != _hash(source):
            raise OSError(f"Local attachment verification failed: {source.name}")
        temporary.replace(destination)
        for candidate in {input_path, f"input/{input_path}"}:
            saved_markdown = saved_markdown.replace(f"![[{candidate}]]", f"![[{vault_path}]]")
        copied.append(vault_path)
    missing = [path for _, path, _ in mappings if f"![[{path}]]" not in saved_markdown]
    if missing:
        saved_markdown += "\n\n## 相关素材\n\n" + "\n".join(f"![[{path}]]" for path in missing)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Collision-free local target unexpectedly exists: {target_relative}")
    content = saved_markdown.rstrip() + "\n"
    temporary = target.with_name(target.name + ".writing")
    temporary.write_text(content, encoding="utf-8")
    if temporary.read_text(encoding="utf-8") != content:
        raise OSError("Local note read-back verification failed")
    temporary.replace(target)
    return job.update(
        status="completed", stage="local_note_saved", note_local_saved=True, note_local_opened=False,
        note_cloud_published=False, note_local_path=str(target), note_attachments=copied,
        note_target=target_relative, note_mode=mode, note_preview=content.rstrip(),
        note_cloud_target=str(cloud_target) if cloud_target else None,
        note_cloud_base_hash=_hash(cloud_target) if cloud_target else None,
    )


def open_local(job: JobWorkspace, settings: Settings) -> dict:
    state = job.read()
    path = Path(state.get("note_local_path", "")).resolve(strict=True)
    local_root = settings.local_obsidian_vault.resolve(strict=True)
    relative = path.relative_to(local_root)
    executable = settings.obsidian_exe.resolve(strict=True)
    vault_id = _ensure_obsidian_vault_registered(local_root, settings)
    uri = (
        "obsidian://open?vault=" + quote(vault_id, safe="")
        + "&file=" + quote(relative.as_posix(), safe="")
    )
    subprocess.Popen([str(executable), uri], cwd=str(executable.parent), close_fds=True)
    return job.update(note_local_opened=True, note_open_uri=uri, note_local_vault_id=vault_id)


def _ensure_obsidian_vault_registered(local_root: Path, settings: Settings) -> str:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("Windows APPDATA is unavailable; cannot register the local Obsidian Vault")
    registry = Path(appdata) / "obsidian" / "obsidian.json"
    if not registry.is_file():
        raise FileNotFoundError(f"Obsidian Vault registry was not found: {registry}")
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OSError(f"Cannot read the Obsidian Vault registry: {registry}") from exc
    vaults = data.get("vaults")
    if not isinstance(vaults, dict):
        raise ValueError("Obsidian Vault registry has an invalid vaults section")
    normalized = os.path.normcase(str(local_root.resolve()))
    for vault_id, entry in vaults.items():
        if isinstance(entry, dict) and os.path.normcase(str(Path(entry.get("path", "")).resolve())) == normalized:
            return vault_id
    vault_id = uuid.uuid4().hex[:16]
    while vault_id in vaults:
        vault_id = uuid.uuid4().hex[:16]
    backup_root = settings.project_root / ".runtime" / "obsidian-config-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / f"{time.strftime('%Y%m%d-%H%M%S')}-obsidian.json"
    shutil.copy2(registry, backup)
    vaults[vault_id] = {"path": str(local_root), "ts": int(time.time() * 1000)}
    temporary = registry.with_name(registry.name + ".research-starter-writing")
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(registry)
    return vault_id


def publish_cloud(job: JobWorkspace, settings: Settings) -> dict:
    state = job.read()
    if not state.get("note_local_saved") or not state.get("note_local_opened"):
        raise ValueError("Open the saved local note in Obsidian before cloud publication")
    target = Path(state["note_local_path"]).resolve(strict=True)
    target_relative = target.relative_to(local_record(settings).resolve(strict=True))
    remote_root = cloud_record(settings).resolve(strict=True)
    remote_target = (remote_root / target_relative).resolve()
    remote_target.relative_to(remote_root)
    if _hash(remote_target) != state.get("note_cloud_base_hash"):
        raise RuntimeError("Cloud note changed after local save; publication stopped to avoid overwriting it")
    bundle = job.temp / f"cloud-publish-{uuid.uuid4().hex}"
    bundle.mkdir(parents=True)
    note_copy = bundle / target_relative
    note_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, note_copy)
    for vault_path in state.get("note_attachments", []):
        relative = Path(vault_path).relative_to(Path(note_root_relative(settings).as_posix()))
        source = (settings.local_obsidian_vault / Path(vault_path)).resolve(strict=True)
        destination = bundle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    result = subprocess.run(
        ["robocopy", str(bundle), str(remote_root), "/E", "/COPY:DAT", "/DCOPY:DAT", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode > 7:
        raise OSError(f"Cloud copy failed with robocopy exit code {result.returncode}: {result.stderr.strip()}")
    published = [remote_target]
    if _hash(remote_target) != _hash(target):
        raise OSError("Published cloud note failed hash verification")
    for vault_path in state.get("note_attachments", []):
        relative = Path(vault_path).relative_to(Path(note_root_relative(settings).as_posix()))
        source = settings.local_obsidian_vault / Path(vault_path)
        destination = remote_root / relative
        if _hash(source) != _hash(destination):
            raise OSError(f"Published attachment failed hash verification: {relative}")
        published.append(destination)
    return job.update(
        status="completed", stage="cloud_note_published", note_cloud_published=True,
        cloud_sync_status="completed", cloud_outputs=[str(path) for path in published],
    )
