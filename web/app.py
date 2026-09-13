"""FastAPI UI for local-only Research Starter jobs."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from runner.codex_client import codex_status
from runner.config import Settings, load_settings
from runner.exchange import validate_icloud_sources
from runner.jobs import JobWorkspace, create_job, default_job_title
from runner.tasks import resume_job, run_existing_job
from runner.preferences import OPTIONAL_PATHS, PATH_LABELS, app_info, bundled_runtime_info, save_preferences
from runner.login import LoginManager
from runner.note_store import initialize_local_vault, open_local, publish_cloud, save_local

settings: Settings = load_settings()
_codex_cache: tuple[float, dict] | None = None
login_manager = LoginManager()
app = FastAPI(title="Research Starter", docs_url=None, redoc_url=None)
ASSET_VERSION = "0.2.1.6"
templates = Jinja2Templates(directory=str(settings.project_root / "web" / "templates"))
templates.env.globals["asset_version"] = ASSET_VERSION
app.mount("/static", StaticFiles(directory=str(settings.project_root / "web" / "static")), name="static")
for vendor_name, vendor_path in {
    "quikchat": settings.project_root / "node_modules" / "quikchat" / "dist",
    "marked": settings.project_root / "node_modules" / "marked" / "lib",
    "dompurify": settings.project_root / "node_modules" / "dompurify" / "dist",
    "pdfjs": settings.project_root / "node_modules" / "pdfjs-dist" / "build",
    "pptx-renderer": settings.project_root / "node_modules" / "@aiden0z" / "pptx-renderer" / "dist",
    "katex": settings.project_root / "node_modules" / "katex" / "dist",
}.items():
    if vendor_path.is_dir():
        app.mount(f"/vendor/{vendor_name}", StaticFiles(directory=str(vendor_path)), name=f"vendor-{vendor_name}")


@app.middleware("http")
async def local_requests_only(request: Request, call_next):
    if request.url.hostname not in {"127.0.0.1", "localhost", "testserver"}:
        return JSONResponse({"detail": "Only local access is supported"}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin writes are not allowed"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


def _require_idle():
    if any(row.get("status") in {"created", "running"} for rows in _jobs_by_task().values() for row in rows):
        raise HTTPException(409, "请等待当前任务完成后再更改设置或账户")


def _job(job_id: str) -> JobWorkspace:
    candidate = (settings.local_jobs / job_id).resolve()
    try:
        candidate.relative_to(settings.local_jobs.resolve())
    except ValueError as exc:
        raise HTTPException(400, "Invalid job id") from exc
    if not (candidate / "job.json").is_file():
        raise HTTPException(404, "Job not found")
    return JobWorkspace(candidate)


def _jobs_by_task() -> dict[str, list[dict]]:
    grouped = {task: [] for task in ("paper-guide", "research-note", "research-slides")}
    if not settings.local_jobs.exists():
        return grouped
    for path in settings.local_jobs.iterdir():
        state_path = path / "job.json"
        if state_path.is_file():
            try:
                row = json.loads(state_path.read_text(encoding="utf-8"))
                if row.get("task") in grouped:
                    row["display_title"] = row.get("title") or default_job_title(row["task"], row.get("source_files", []))
                    grouped[row["task"]].append(row)
            except (OSError, json.JSONDecodeError):
                continue
    for rows in grouped.values():
        rows.sort(key=lambda row: (bool(row.get("starred")), row.get("created_at", "")), reverse=True)
    return grouped


def _present_job(job: JobWorkspace) -> dict:
    state = job.read()
    state["input_files"] = [
        path.relative_to(job.input).as_posix()
        for path in job.input.rglob("*") if path.is_file()
    ]
    pdfs = [path for path in state["input_files"] if Path(path).suffix.lower() == ".pdf"]
    state["paper_file"] = pdfs[0] if state.get("task") == "paper-guide" and pdfs else None
    state["display_title"] = state.get("title") or default_job_title(state.get("task", ""), state.get("source_files", []))
    state["cloud_obsidian_enabled"] = settings.obsidian_vault is not None and settings.obsidian_write_root is not None
    state["pptx_output_index"] = next(
        (index for index, output in enumerate(state.get("outputs", [])) if output == state.get("latest_pptx")),
        None,
    )
    if state["pptx_output_index"] is None:
        state["pptx_output_index"] = next(
        (index for index, output in enumerate(state.get("outputs", [])) if Path(output).suffix.lower() == ".pptx"),
        None,
        )
    if state.get("task") == "research-slides":
        outputs = state.get("outputs", [])
        revisions = state.get("slides_revisions", [])
        revision_by_path = {
            os.path.normcase(str(Path(item.get("path", "")))): item
            for item in revisions if item.get("path")
        }
        ordered = [
            (index, output, None) for index, output in enumerate(outputs)
            if Path(output).suffix.lower() == ".pptx"
            and os.path.normcase(str(Path(output))) not in revision_by_path
        ]
        for revision in revisions:
            revision_path = os.path.normcase(str(Path(revision.get("path", ""))))
            match = next(
                ((index, output, revision) for index, output in enumerate(outputs)
                 if os.path.normcase(str(Path(output))) == revision_path),
                None,
            )
            if match:
                ordered.append(match)
        known = {index for index, _, _ in ordered}
        ordered.extend(
            (index, output, None) for index, output in enumerate(outputs)
            if index not in known and Path(output).suffix.lower() == ".pptx"
        )
        versions = []
        for number, (index, output, revision) in enumerate(ordered, 1):
            feedback = " ".join(str((revision or {}).get("instructions", "")).split())
            kind = "初始版本" if number == 1 else f"第 {number - 1} 次修订"
            label = f"V{number} · {kind}" + (f" · {feedback[:28]}" if feedback else "")
            versions.append({
                "index": index, "version": number, "label": label, "feedback": feedback,
                "latest": output == state.get("latest_pptx") or (
                    not state.get("latest_pptx") and index == state["pptx_output_index"]
                ),
            })
        state["pptx_versions"] = versions
    return state


def _icloud_items(task: str) -> list[str]:
    if settings.icloud_inbox_root is None:
        return []
    root = settings.icloud_inbox_root / task
    if not root.is_dir():
        return []
    return [str(path.relative_to(root)) for path in sorted(root.iterdir(), key=lambda p: p.name.lower())]


def _safe_upload_parts(filename: str) -> tuple[str, ...]:
    normalized = filename.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized:
        raise HTTPException(400, f"Invalid upload path: {filename}")
    parts = tuple(part for part in normalized.split("/") if part not in {"", "."})
    if not parts or ".." in parts:
        raise HTTPException(400, f"Invalid upload path: {filename}")
    return parts


def _validate_source_shape(task: str, sources: list[Path]) -> None:
    if task == "paper-guide":
        if len(sources) != 1 or not sources[0].is_file() or sources[0].suffix.lower() != ".pdf":
            raise HTTPException(400, "Paper Guide requires exactly one PDF file")
        return
    if len(sources) != 1 or not sources[0].is_dir():
        raise HTTPException(400, f"{task} requires exactly one material folder")


async def _save_uploads(task: str, files: list[UploadFile]) -> list[Path]:
    staging = settings.project_root / ".runtime" / "uploads" / uuid.uuid4().hex
    staging.mkdir(parents=True, exist_ok=False)
    try:
        uploaded_paths: list[Path] = []
        seen: set[tuple[str, ...]] = set()
        for upload in files:
            if not upload.filename:
                continue
            parts = _safe_upload_parts(upload.filename)
            if parts in seen:
                raise HTTPException(400, f"Duplicate upload path: {upload.filename}")
            seen.add(parts)
            destination = staging.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    handle.write(chunk)
            uploaded_paths.append(destination)
        if not uploaded_paths:
            raise HTTPException(400, "No material was provided")

        if task == "paper-guide":
            sources = uploaded_paths
        else:
            top_levels = {path.relative_to(staging).parts[0] for path in uploaded_paths}
            if len(top_levels) != 1 or any(len(path.relative_to(staging).parts) < 2 for path in uploaded_paths):
                raise HTTPException(400, f"{task} requires one uploaded folder, not loose files")
            sources = [staging / next(iter(top_levels))]
        _validate_source_shape(task, sources)
        return sources
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


async def _execute(job: JobWorkspace, instructions: str, icloud: bool) -> None:
    try:
        state = job.read()
        await run_existing_job(
            job,
            instructions,
            settings=settings,
            icloud=icloud,
            model=None if state.get("model") == "runtime default" else state.get("model"),
            effort=None if state.get("reasoning_effort") == "runtime default" else state.get("reasoning_effort"),
            language=state.get("language", "zh"),
        )
    except Exception:
        pass


async def _resume(job: JobWorkspace, instructions: str) -> None:
    try:
        await resume_job(job.root, instructions, settings=settings)
    except Exception:
        pass


async def _revise_slides(job: JobWorkspace, feedback: str) -> None:
    try:
        await resume_job(job.root, feedback, settings=settings, operation="slides_revision")
    except Exception:
        pass


async def _revise_note(job: JobWorkspace, feedback: str) -> None:
    try:
        await resume_job(
            job.root,
            "Revise the current Research Note preview using the user's feedback below. Return the complete "
            "replacement Markdown preview, not a patch, changelog, confirmation, or process commentary. "
            "Do not write to the Vault yet. Preserve and correctly position relevant image/GIF embeds.\n\n"
            f"User feedback:\n{feedback}",
            settings=settings,
            operation="note_revision",
        )
    except Exception:
        pass


async def _save_note_local(job: JobWorkspace) -> None:
    try:
        save_local(job, settings)
        job.update(note_save_status="completed")
    except Exception as exc:
        job.update(
            status="failed",
            stage="local_note_save",
            note_save_status="failed",
            note_save_error=f"{type(exc).__name__}: {exc}",
            error=f"{type(exc).__name__}: {exc}",
        )


async def _publish_note_cloud(job: JobWorkspace) -> None:
    try:
        publish_cloud(job, settings)
    except Exception as exc:
        job.update(
            status="failed", stage="cloud_note_publish", cloud_sync_status="failed",
            cloud_error=f"{type(exc).__name__}: {exc}", error=f"{type(exc).__name__}: {exc}",
        )


async def _save_ppt_template(job: JobWorkspace, upload: UploadFile) -> Path:
    if not upload.filename:
        raise HTTPException(400, "PPT template filename is missing")
    parts = _safe_upload_parts(upload.filename)
    if len(parts) != 1 or Path(parts[0]).suffix.lower() != ".pptx":
        raise HTTPException(400, "PPT template must be one .pptx file")
    destination = job.root / "template" / parts[0]
    destination.parent.mkdir(parents=True, exist_ok=False)
    with destination.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            handle.write(chunk)
    if destination.stat().st_size == 0:
        raise HTTPException(400, "PPT template is empty")
    return destination


async def _get_codex_status(*, refresh: bool = False) -> dict:
    global _codex_cache
    if not refresh and _codex_cache and time.monotonic() - _codex_cache[0] < 30:
        return _codex_cache[1]
    value = await codex_status(settings.codex_home, settings.project_root)
    _codex_cache = (time.monotonic(), value)
    return value


async def _validate_codex_selection(model: str, effort: str) -> None:
    if not model and not effort:
        return
    status = await _get_codex_status()
    models = {item["model"]: item for item in status["models"]["data"] if not item.get("hidden")}
    if model not in models:
        raise HTTPException(400, "Selected Codex model is unavailable")
    supported = {item["reasoningEffort"] for item in models[model]["supportedReasoningEfforts"]}
    if effort not in supported:
        raise HTTPException(400, "Selected reasoning effort is unavailable for this model")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"jobs_by_task": _jobs_by_task()})


@app.get("/tasks/{task}", response_class=HTMLResponse)
async def task_page(request: Request, task: str):
    if task not in {"paper-guide", "research-note", "research-slides"}:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request,
        "task.html",
        {"task": task, "icloud_items": _icloud_items(task), "icloud_enabled": settings.icloud_inbox_root is not None},
    )


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: str):
    return templates.TemplateResponse(request, "job.html", {"job": _present_job(_job(job_id))})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {
        "settings": {
            key: "" if getattr(settings, key) is None else str(getattr(settings, key))
            for key in PATH_LABELS
        },
        "labels": PATH_LABELS, "optional_paths": OPTIONAL_PATHS,
        "runtime": bundled_runtime_info(settings), "info": app_info(settings.project_root),
    })


@app.post("/api/settings")
async def update_settings(request: Request):
    global settings, _codex_cache
    _require_idle()
    if login_manager.active:
        raise HTTPException(409, "请先完成或取消登录")
    try:
        values = await request.json()
        if not isinstance(values, dict):
            raise ValueError("设置格式不正确")
        settings = save_preferences(settings, values)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    _codex_cache = None
    return {"message": "已保存并生效；原配置已备份。已有文件不会自动搬迁。"}


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html", {"info": app_info(settings.project_root)})


@app.get("/guide", response_class=HTMLResponse)
async def guide_page(request: Request):
    content = (settings.project_root / "USER_GUIDE.md").read_text(encoding="utf-8")
    return templates.TemplateResponse(request, "guide.html", {"content": content})


@app.post("/api/codex/login")
async def start_login():
    _require_idle()
    return await login_manager.start(settings)


@app.get("/api/codex/login")
async def login_status():
    global _codex_cache
    if login_manager.state["status"] == "completed":
        _codex_cache = None
    return login_manager.state


@app.post("/api/codex/login/cancel")
async def cancel_login():
    return await login_manager.cancel()


@app.post("/api/jobs")
async def submit_job(
    background: BackgroundTasks,
    task: str = Form(...),
    instructions: str = Form(""),
    icloud_item: str = Form(""),
    model: str = Form(""),
    effort: str = Form(""),
    language: str = Form("zh"),
    files: list[UploadFile] = File(default=[]),
    ppt_template: UploadFile | None = File(default=None),
):
    if login_manager.active:
        raise HTTPException(409, "请先完成或取消 Codex 登录")
    if task not in {"paper-guide", "research-note", "research-slides"}:
        raise HTTPException(400, "Unsupported task")
    if language not in {"zh", "ja", "en"}:
        raise HTTPException(400, "Unsupported output language")
    await _validate_codex_selection(model, effort)
    use_icloud = bool(icloud_item)
    if use_icloud:
        if settings.icloud_inbox_root is None:
            raise HTTPException(400, "iCloud 素材入口未配置，请改用本地上传或先在 Settings 中填写")
        try:
            root = (settings.icloud_inbox_root / task).resolve(strict=True)
            source = (root / icloud_item).resolve(strict=True)
            sources = validate_icloud_sources(task, [source], settings)
            _validate_source_shape(task, sources)
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise HTTPException(400, f"Invalid or unavailable iCloud input: {exc}") from exc
    else:
        sources = await _save_uploads(task, files)
    job = create_job(settings.local_jobs, task, sources)
    if task == "research-note":
        try:
            initialize_local_vault(settings)
        except (OSError, RuntimeError, ValueError) as exc:
            shutil.rmtree(job.root)
            raise HTTPException(400, f"无法准备项目本地 Obsidian：{exc}") from exc
    if ppt_template and ppt_template.filename:
        if task != "research-slides":
            raise HTTPException(400, "PPT template is only available for Research Slides")
        template_path = await _save_ppt_template(job, ppt_template)
        job.update(template_path=str(template_path))
    job.update(
        model=model or "runtime default",
        reasoning_effort=effort or "runtime default",
        language=language,
    )
    if use_icloud:
        job.update(cloud_sync_status="copied_in")
    if task == "research-note":
        instructions = (
            "Preview only. Search the Vault and propose the exact Markdown and target path. "
            "Do not write, append, overwrite, move, rename, or delete anything yet. " + instructions
        )
    background.add_task(_execute, job, instructions, use_icloud)
    return JSONResponse({"job_id": job.root.name}, status_code=202)


@app.get("/api/codex/status")
async def api_codex_status(refresh: bool = False):
    try:
        return await _get_codex_status(refresh=refresh)
    except Exception as exc:
        raise HTTPException(503, f"Codex status unavailable: {type(exc).__name__}") from exc


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    return _present_job(_job(job_id))


@app.post("/api/jobs/{job_id}/star")
async def toggle_job_star(job_id: str):
    job = _job(job_id)
    state = job.update(starred=not bool(job.read().get("starred")))
    return {"job_id": job_id, "starred": state["starred"]}


@app.post("/api/jobs/{job_id}/title")
async def update_job_title(job_id: str, title: str = Form(...)):
    normalized = " ".join(title.split())
    if not normalized or len(normalized) > 40:
        raise HTTPException(400, "Title must contain 1 to 40 characters")
    state = _job(job_id).update(title=normalized)
    return {"job_id": job_id, "title": state["title"]}


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    job = _job(job_id)
    root = job.root.resolve(strict=True)
    root.relative_to(settings.local_jobs.resolve(strict=True))
    shutil.rmtree(root)
    return {"deleted": job_id}


@app.post("/api/jobs/{job_id}/follow-up")
async def follow_up(background: BackgroundTasks, job_id: str, question: str = Form(...), model: str = Form(""), effort: str = Form("")):
    job = _job(job_id)
    if job.read()["task"] != "paper-guide":
        raise HTTPException(400, "Follow-up is only enabled for Paper Guide")
    if job.read().get("status") not in {"completed", "failed"} or not job.read().get("thread_id") or login_manager.active:
        raise HTTPException(409, "当前会话尚不能追问，请等待任务或登录完成")
    if not question.strip():
        raise HTTPException(400, "请输入问题")
    await _validate_codex_selection(model, effort)
    if job.read().get("status") not in {"completed", "failed"}:
        raise HTTPException(409, "已有追问正在执行")
    if model:
        job.update(model=model, reasoning_effort=effort)
    job.update(status="running", stage="running_follow_up", error=None)
    background.add_task(_resume, job, question)
    return JSONResponse({"job_id": job_id}, status_code=202)


@app.post("/api/jobs/{job_id}/revise-slides")
async def revise_slides(background: BackgroundTasks, job_id: str, feedback: str = Form(...)):
    job = _job(job_id)
    state = job.read()
    if state["task"] != "research-slides":
        raise HTTPException(400, "Only Research Slides supports this operation")
    if state.get("status") not in {"completed", "failed"} or not state.get("thread_id") or login_manager.active:
        raise HTTPException(409, "请等待当前任务或登录完成")
    if not feedback.strip():
        raise HTTPException(400, "请输入修改建议")
    job.update(status="running", stage="revising_slides", error=None)
    background.add_task(_revise_slides, job, feedback.strip())
    return JSONResponse({"job_id": job_id}, status_code=202)


@app.post("/api/jobs/{job_id}/revise-note")
async def revise_note(background: BackgroundTasks, job_id: str, feedback: str = Form(...)):
    job = _job(job_id)
    state = job.read()
    if state["task"] != "research-note":
        raise HTTPException(400, "Revision is only enabled for Research Note")
    if state.get("status") != "completed" or state.get("note_local_saved"):
        raise HTTPException(409, "This note is not available for revision")
    feedback = feedback.strip()
    if not feedback:
        raise HTTPException(400, "Revision feedback is required")
    job.update(status="running", stage="revising_note", error=None)
    background.add_task(_revise_note, job, feedback)
    return JSONResponse({"job_id": job_id}, status_code=202)


@app.post("/api/jobs/{job_id}/save-note")
async def save_note(background: BackgroundTasks, job_id: str):
    job = _job(job_id)
    state = job.read()
    if state["task"] != "research-note":
        raise HTTPException(400, "Not a Research Note job")
    if state.get("note_local_saved") or state.get("note_save_status") in {"copying_local_attachments", "writing_local_markdown"}:
        raise HTTPException(409, "This note is already saved locally or currently being saved")
    if state.get("status") != "completed":
        raise HTTPException(409, "The preview is not ready to save")
    job.update(status="running", stage="saving_local_note", note_save_status="writing_local_markdown", error=None)
    background.add_task(
        _save_note_local,
        job,
    )
    return JSONResponse({"job_id": job_id}, status_code=202)


@app.post("/api/jobs/{job_id}/open-local-note")
async def open_local_note(job_id: str):
    job = _job(job_id)
    state = job.read()
    if state.get("task") != "research-note" or not state.get("note_local_saved"):
        raise HTTPException(409, "请先确认并写入本地 Obsidian")
    try:
        result = open_local(job, settings)
    except (OSError, ValueError) as exc:
        raise HTTPException(500, f"无法打开本地笔记：{exc}") from exc
    return {"job_id": job_id, "note_local_opened": result["note_local_opened"]}


@app.post("/api/jobs/{job_id}/publish-note")
async def publish_note(background: BackgroundTasks, job_id: str):
    job = _job(job_id)
    state = job.read()
    if state.get("task") != "research-note" or not state.get("note_local_saved"):
        raise HTTPException(409, "请先写入本地 Obsidian")
    if settings.obsidian_vault is None or settings.obsidian_write_root is None:
        raise HTTPException(409, "云端 Obsidian 未配置；本地笔记可以继续正常使用")
    if not state.get("note_local_opened"):
        raise HTTPException(409, "请先在本地 Obsidian 中打开笔记进行检查")
    if state.get("note_cloud_published") or state.get("cloud_sync_status") == "publishing":
        raise HTTPException(409, "该版本已经发布或正在发布")
    job.update(status="running", stage="publishing_note_cloud", cloud_sync_status="publishing", error=None)
    background.add_task(_publish_note_cloud, job)
    return JSONResponse({"job_id": job_id}, status_code=202)


@app.get("/jobs/{job_id}/output/{index}")
async def download_output(job_id: str, index: int):
    job = _job(job_id)
    state = job.read()
    outputs = state.get("outputs", [])
    if index < 0 or index >= len(outputs):
        raise HTTPException(404)
    path = Path(outputs[index]).resolve(strict=True)
    try:
        path.relative_to(job.output.resolve())
    except ValueError as exc:
        raise HTTPException(400, "Output path is outside the job workspace") from exc
    filename = path.name
    if state.get("task") == "research-slides" and path.suffix.lower() == ".pptx":
        presented = _present_job(job)
        version = next((item for item in presented.get("pptx_versions", []) if item["index"] == index), None)
        if version:
            title = re.sub(r'[<>:"/\\|?*]+', "-", presented.get("display_title", "Research-Slides")).strip(" .")
            kind = "初始版" if version["version"] == 1 else f"修订版-{version['version'] - 1}"
            filename = f"{title}-V{version['version']}-{kind}.pptx"
    return FileResponse(path, filename=filename)


@app.get("/jobs/{job_id}/input/{relative_path:path}")
async def read_job_input(job_id: str, relative_path: str):
    job = _job(job_id)
    path = (job.input / relative_path).resolve(strict=True)
    try:
        path.relative_to(job.input.resolve(strict=True))
    except ValueError as exc:
        raise HTTPException(400, "Input path is outside the job workspace") from exc
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


@app.post("/jobs/{job_id}/open-folder")
async def open_folder(job_id: str):
    job = _job(job_id)
    if os.name != "nt":
        raise HTTPException(501, "Folder opening is currently implemented for Windows only")
    os.startfile(job.output)  # type: ignore[attr-defined]
    return {"opened": str(job.output)}


@app.get("/health")
async def health():
    return {"status": "ok", "host": "127.0.0.1"}
