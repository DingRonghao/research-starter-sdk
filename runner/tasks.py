"""Phase 1 task orchestration for the three unchanged Skills."""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Iterable

from .codex_client import CodexRunner
from .config import Settings, load_settings
from .exchange import publish_outputs, validate_icloud_sources
from .jobs import JobWorkspace, create_job, default_job_title
from .note_store import independent_target, note_root_relative, parse_preview

TASKS = {"paper-guide", "research-note", "research-slides"}


def _final_text(result: object) -> str:
    value = getattr(result, "final_response", None)
    return value if isinstance(value, str) else str(result)


TITLE_PATTERN = re.compile(
    r"\s*<research-starter-title>\s*([^<]{1,80}?)\s*</research-starter-title>\s*",
    re.IGNORECASE,
)


def _response_and_title(result: object) -> tuple[str, str | None]:
    text = _final_text(result)
    match = TITLE_PATTERN.search(text)
    title = " ".join(match.group(1).split())[:40] if match else None
    return TITLE_PATTERN.sub("\n", text).strip(), title


def _outputs(job: JobWorkspace) -> list[str]:
    return [str(path) for path in job.output.rglob("*") if path.is_file()]


LANGUAGES = {"zh": "Simplified Chinese", "ja": "Japanese", "en": "English"}


def _skill_prompt(task: str, job: JobWorkspace, instructions: str, settings: Settings, language: str) -> str:
    language_instruction = (
        f"Write all user-facing content and generated prose in {LANGUAGES[language]}. "
        "Preserve source titles, quotations, code, formulas, and proper nouns when translation would be harmful. "
        "At the very end of your final response, add exactly one hidden metadata marker in the form "
        "<research-starter-title>不超过18个汉字的中文项目概括</research-starter-title>. "
    )
    if task == "paper-guide":
        return (
            language_instruction + "Use the supplied paper-guide Skill. The user-provided PDF is under "
            f"{job.input}. Use this project's Docling executable at {settings.docling_exe}. "
            "Keep all parsing intermediates under the job temp directory "
            f"{job.temp}. Return the complete six-part reading guide directly in your final response so it "
            "appears as the first assistant message in the web conversation. Do not create reading-guide.md "
            "or any other final guide file, and do not merely report that a file was exported. "
            f"User instructions: {instructions or 'Provide the standard six-part reading guide.'}"
        )
    if task == "research-slides":
        template_path = job.read().get("template_path")
        template_instruction = (
            f"A PPTX design template is provided at {template_path}. Treat its slides as a layout and visual "
            "library, not as content that must all remain. Inspect every template slide, select only the layouts "
            "needed for this presentation, duplicate or adapt those slides in a new working copy, replace their "
            "placeholder/sample content, and remove every unused template slide. Preserve the selected slides' "
            "masters, theme, typography, palette, repeated branding, spacing, and footer system. Never append a "
            "separately styled deck after the intact template, and never leave sample text, unused example pages, "
            "or an ending slide before content. Do not overwrite the uploaded template. "
            if template_path else
            "No template was supplied. Use the Skill's default minimal academic style. "
        )
        return (
            language_instruction + "Use the supplied research-slides Skill. Inventory every file under "
            f"{job.input}. Use the Skill's existing generate_slides.mjs and the project-local "
            f"Node dependencies. {template_instruction}Generate the final editable PPTX only under {job.output}. "
            f"User instructions: {instructions or 'Infer the page structure conservatively from the text files and other materials in the input folder.'}"
        )
    note_root = note_root_relative(settings).as_posix()
    return (
        language_instruction + "Use the supplied research-note Skill for analysis and preview only. The local "
        f"read-only knowledge mirror is {settings.local_obsidian_vault / Path(note_root)}. "
        "Do not write any file and do not call notesmd-cli. Return exactly one safe target under "
        f"{note_root} using <research-note-target>...</research-note-target>, followed by "
        "<research-note-mode>create</research-note-mode>, followed by one complete fenced Markdown block. "
        "Every task is an independent note version; never propose appending to an existing note. "
        f"Job input is stored at {job.input}. User instructions: {instructions}"
    )


async def run_task(
    task: str,
    sources: Iterable[Path],
    instructions: str,
    *,
    settings: Settings | None = None,
    thread_id: str | None = None,
    icloud: bool = False,
    model: str | None = None,
    effort: str | None = None,
    language: str = "zh",
    model_provider: str = "openai",
) -> JobWorkspace:
    if task not in TASKS:
        raise ValueError(f"Unsupported task: {task}")
    settings = settings or load_settings()
    source_list = list(sources)
    if icloud:
        source_list = validate_icloud_sources(task, source_list, settings)
    job = create_job(settings.local_jobs, task, source_list)
    if icloud:
        job.update(cloud_sync_status="copied_in")
    return await run_existing_job(
        job,
        instructions,
        settings=settings,
        icloud=icloud,
        thread_id=thread_id,
        model=model,
        effort=effort,
        language=language,
        model_provider=model_provider,
    )


async def run_existing_job(
    job: JobWorkspace,
    instructions: str,
    *,
    settings: Settings | None = None,
    icloud: bool = False,
    thread_id: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    language: str = "zh",
    model_provider: str | None = None,
) -> JobWorkspace:
    settings = settings or load_settings()
    task = job.read()["task"]
    model_provider = model_provider or job.read().get("model_provider", "openai")
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    cwd = settings.local_obsidian_vault if task == "research-note" else job.root
    skill_path = settings.skills_root / task
    try:
        job.update(
            status="running",
            stage="running_codex",
            model=model or "runtime default",
            reasoning_effort=effort or "runtime default",
            model_provider=model_provider,
            language=language,
        )
        job.log("starting Codex skill turn")
        async with CodexRunner(settings.codex_home, settings.project_root, model_provider) as runner:
            actual_thread_id, result = await runner.run_skill(
                skill_name=task,
                skill_path=skill_path,
                prompt=_skill_prompt(task, job, instructions, settings, language),
                cwd=cwd,
                thread_id=thread_id,
                model=model,
                effort=effort,
            )
        final_response, generated_title = _response_and_title(result)
        note_updates = {}
        if task == "research-note":
            note_target, note_mode, note_markdown = parse_preview(final_response, settings)
            note_target = independent_target(note_target, language, settings)
            note_updates = {"note_target": note_target, "note_mode": "create", "note_preview": note_markdown}
        local_outputs = _outputs(job)
        current_state = job.read()
        job.update(
            status="completed",
            stage="completed",
            thread_id=actual_thread_id,
            outputs=local_outputs,
            final_response=final_response,
            initial_response=current_state.get("initial_response") or final_response,
            **note_updates,
            title=generated_title or current_state.get("title") or default_job_title(task, current_state.get("source_files", [])),
        )
        if icloud and task == "research-slides":
            if settings.icloud_output_root is None:
                job.update(stage="completed", cloud_sync_status="not_configured")
                job.log("job completed; iCloud output is not configured")
                return job
            try:
                job.update(stage="publishing_output")
                cloud_outputs = publish_outputs(task, job, settings)
                job.update(
                    stage="completed",
                    cloud_sync_status="completed",
                    cloud_outputs=[str(path) for path in cloud_outputs],
                )
            except Exception as cloud_error:
                job.update(
                    stage="completed",
                    cloud_sync_status="failed",
                    cloud_error=f"{type(cloud_error).__name__}: {cloud_error}",
                )
        elif icloud:
            job.update(cloud_sync_status="not_applicable")
        job.log("job completed")
        return job
    except Exception as exc:
        job.update(status="failed", stage="skill_execution", error=f"{type(exc).__name__}: {exc}")
        job.log(f"job failed: {type(exc).__name__}: {exc}")
        raise


async def resume_job(
    job_root: Path,
    instructions: str,
    settings: Settings | None = None,
    *,
    model: str | None = None,
    effort: str | None = None,
    operation: str = "follow_up",
) -> JobWorkspace:
    settings = settings or load_settings()
    job = JobWorkspace(job_root.resolve(strict=True))
    state = job.read()
    task = state["task"]
    thread_id = state.get("thread_id")
    model = model or (state.get("model") if state.get("model") != "runtime default" else None)
    effort = effort or (
        state.get("reasoning_effort") if state.get("reasoning_effort") != "runtime default" else None
    )
    model_provider = state.get("model_provider", "openai")
    if task not in TASKS or not thread_id:
        raise ValueError("Job does not contain a resumable task and thread_id")
    cwd = settings.local_obsidian_vault if task == "research-note" else job.root
    skill_path = settings.skills_root / task
    try:
        stages = {"follow_up": "running_follow_up", "note_revision": "revising_note", "slides_revision": "revising_slides"}
        if operation not in stages:
            raise ValueError(f"Unsupported resume operation: {operation}")
        job.update(status="running", stage=stages[operation], error=None)
        prompt = instructions
        include_skill = True
        if task == "paper-guide" and operation == "follow_up":
            include_skill = False
            prompt = (
                "Continue the existing Paper Guide conversation and answer the user's new question directly. "
                f"Respond in {LANGUAGES[state.get('language', 'zh')]}. "
                f"Treat the PDF and the existing Docling Markdown/JSON under {job.temp} as the authoritative "
                "source. Re-read the relevant parsed passages before making paper-specific factual claims, and "
                "give page/section/figure/equation/table locations when useful. Reuse the existing parsed files; "
                "do not rerun Docling unless they are missing or unreadable. Do not regenerate the initial "
                "six-part reading guide unless the user explicitly asks for it. Preserve uncertainty rather than "
                f"guessing.\n\nUser question:\n{instructions}"
            )
        if task == "research-note":
            prompt = _skill_prompt(task, job, instructions, settings, state.get("language", "zh"))
        if operation == "slides_revision":
            revision_path = job.output / f"revision-{uuid.uuid4().hex[:10]}.pptx"
            prompt = _skill_prompt(task, job, instructions, settings, state.get("language", "zh")) + (
                f"\nRevise the latest deck {state.get('latest_pptx') or state.get('outputs', [])} using the feedback. "
                f"Save the complete revised deck ONLY at {revision_path}. Keep all previous outputs intact. "
                "Re-use the existing material and narrative unless feedback changes them. Preserve any supplied "
                "template: rebuild a complete working copy from the ORIGINAL template's selected layouts, replace "
                "the relevant content, and remove unused template pages. Never append a separately styled deck to "
                "either the original template or a previous result. Validate the resulting PPTX."
            )
        job.log("starting Codex follow-up turn")
        async with CodexRunner(settings.codex_home, settings.project_root, model_provider) as runner:
            actual_thread_id, result = await runner.run_skill(
                skill_name=task,
                skill_path=skill_path,
                prompt=prompt,
                cwd=cwd,
                thread_id=thread_id,
                model=model,
                effort=effort,
                include_skill=include_skill,
            )
        response, generated_title = _response_and_title(result)
        updates = dict(
            status="completed",
            stage="completed",
            thread_id=actual_thread_id,
            outputs=_outputs(job),
        )
        if generated_title:
            updates["title"] = generated_title
        if operation == "follow_up":
            follow_ups = list(state.get("follow_ups", []))
            follow_ups.append({"instructions": instructions, "response": response})
            updates.update(final_response=response, follow_ups=follow_ups)
        elif operation == "note_revision":
            note_target, note_mode, note_markdown = parse_preview(response, settings)
            note_target = state.get("note_target") or independent_target(
                note_target, state.get("language", "zh"), settings
            )
            revisions = list(state.get("note_revisions", []))
            revisions.append({"instructions": instructions, "response": response})
            updates.update(
                final_response=response, note_preview=note_markdown, note_target=note_target,
                note_mode="create", note_revisions=revisions,
            )
        elif operation == "slides_revision":
            with zipfile.ZipFile(revision_path) as archive:
                if "ppt/presentation.xml" not in archive.namelist() or archive.testzip():
                    raise ValueError("修订版 PPTX 不完整，请重试")
            revisions = list(state.get("slides_revisions", []))
            revisions.append({"instructions": instructions, "response": response, "path": str(revision_path)})
            updates.update(final_response=response, latest_pptx=str(revision_path), slides_revisions=revisions)
        job.update(**updates)
        job.log("follow-up completed")
        return job
    except Exception as exc:
        job.update(status="failed", stage=operation, error=f"{type(exc).__name__}: {exc}")
        job.log(f"follow-up failed: {type(exc).__name__}: {exc}")
        raise


def main() -> None:
    import argparse

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=sorted(TASKS))
    parser.add_argument("sources", nargs="*", type=Path)
    parser.add_argument("--instructions", default="")
    parser.add_argument("--thread-id")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--language", choices=sorted(LANGUAGES), default="zh")
    parser.add_argument("--resume-job", type=Path)
    parser.add_argument("--icloud", action="store_true")
    args = parser.parse_args()
    if args.resume_job:
        job = asyncio.run(resume_job(args.resume_job, args.instructions))
    else:
        job = asyncio.run(
            run_task(
                args.task,
                args.sources,
                args.instructions,
                thread_id=args.thread_id,
                icloud=args.icloud,
                model=args.model,
                effort=args.effort,
                language=args.language,
            )
        )
    print(json.dumps(job.read(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
