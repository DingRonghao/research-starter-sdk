import asyncio
import io
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

import web.app as web_app
import runner.tasks as runner_tasks
from runner.note_store import save_local
from runner.template_assets import install_profile


class FolderUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original_settings = web_app.settings
        self.original_execute = web_app._execute
        self.original_execute_template_analysis = web_app._execute_template_analysis
        web_app.settings = replace(
            self.original_settings,
            project_root=self.root,
            local_jobs=self.root / "jobs",
            icloud_inbox_root=self.root / "icloud" / "Inbox",
            obsidian_vault=self.root / "vault",
            obsidian_write_root=self.root / "vault" / "notes",
            local_obsidian_vault=self.root / "local-vault",
            obsidian_exe=self.root / "Obsidian.exe",
        )
        web_app.settings.local_jobs.mkdir(parents=True)
        web_app.settings.obsidian_write_root.mkdir(parents=True)
        web_app.settings.obsidian_exe.write_bytes(b"test fixture")
        for task in ("paper-guide", "research-note", "research-slides"):
            (web_app.settings.icloud_inbox_root / task).mkdir(parents=True)

        async def no_execute(*_args, **_kwargs) -> None:
            return None

        web_app._execute = no_execute
        web_app._execute_template_analysis = no_execute

    def tearDown(self) -> None:
        web_app._execute = self.original_execute
        web_app._execute_template_analysis = self.original_execute_template_analysis
        web_app.settings = self.original_settings
        self.temporary.cleanup()

    def upload(self, name: str, content: bytes = b"test") -> UploadFile:
        return UploadFile(filename=name, file=io.BytesIO(content))

    def install_template_profile(self, template: Path, slide_count: int = 1) -> None:
        generated = self.root / "generated-profile"
        generated.mkdir(exist_ok=True)
        (generated / "profile.json").write_text(json.dumps({
            "schema_version": 1,
            "template_name": template.name,
            "slide_count": slide_count,
            "slides": [{
                "slide_number": 1, "visual_role": "封面", "suitable_for": ["标题"],
                "capacity": {"summary": "短标题"}, "objects": [],
            }],
        }, ensure_ascii=False), encoding="utf-8")
        (generated / "profile.md").write_text("# Template profile\n", encoding="utf-8")
        install_profile(template.parent, template, generated)

    def test_research_note_preserves_one_folder_tree(self) -> None:
        sources = asyncio.run(
            web_app._save_uploads(
                "research-note",
                [
                    self.upload("materials/papers/a.txt", b"A"),
                    self.upload("materials/images/b.png", b"B"),
                ],
            )
        )
        self.assertEqual(["materials"], [source.name for source in sources])
        self.assertEqual(b"A", (sources[0] / "papers" / "a.txt").read_bytes())
        self.assertEqual(b"B", (sources[0] / "images" / "b.png").read_bytes())
        self.assertEqual(self.root / "Inbox" / "research-note", sources[0].parent)

    def test_research_slides_rejects_loose_files(self) -> None:
        with self.assertRaisesRegex(HTTPException, "uploaded folder"):
            asyncio.run(
                web_app._save_uploads(
                    "research-slides",
                    [self.upload("a.txt"), self.upload("b.txt")],
                )
            )

    def test_folder_upload_rejects_multiple_roots(self) -> None:
        with self.assertRaisesRegex(HTTPException, "one uploaded folder"):
            asyncio.run(
                web_app._save_uploads(
                    "research-note",
                    [self.upload("one/a.txt"), self.upload("two/b.txt")],
                )
            )

    def test_upload_rejects_parent_traversal(self) -> None:
        with self.assertRaisesRegex(HTTPException, "Invalid upload path"):
            asyncio.run(
                web_app._save_uploads(
                    "research-note",
                    [self.upload("materials/../outside.txt")],
                )
            )

    def test_endpoint_requires_note_material_folder_but_not_text(self) -> None:
        with TestClient(web_app.app) as client:
            missing = client.post("/api/jobs", data={"task": "research-note"})
            self.assertEqual(400, missing.status_code)

            response = client.post(
                "/api/jobs",
                data={"task": "research-note", "instructions": ""},
                files=[
                    ("files", ("materials/a.txt", b"A", "text/plain")),
                    ("files", ("materials/sub/b.txt", b"B", "text/plain")),
                ],
            )
        self.assertEqual(202, response.status_code)
        job_id = response.json()["job_id"]
        job_input = web_app.settings.local_jobs / job_id / "input" / "materials"
        self.assertEqual(b"A", (job_input / "a.txt").read_bytes())
        self.assertEqual(b"B", (job_input / "sub" / "b.txt").read_bytes())
        self.assertEqual(b"A", (self.root / "Inbox" / "research-note" / "materials" / "a.txt").read_bytes())

    def test_endpoint_can_run_from_existing_project_inbox(self) -> None:
        source = self.root / "Inbox" / "research-note" / "existing-sample"
        source.mkdir(parents=True)
        (source / "notes.md").write_text("sample", encoding="utf-8")
        with TestClient(web_app.app) as client:
            page = client.get("/tasks/research-note")
            response = client.post(
                "/api/jobs",
                data={"task": "research-note", "inbox_item": "existing-sample"},
            )
        self.assertIn("existing-sample", page.text)
        self.assertEqual(202, response.status_code)
        job_input = web_app.settings.local_jobs / response.json()["job_id"] / "input" / "existing-sample" / "notes.md"
        self.assertEqual("sample", job_input.read_text(encoding="utf-8"))

    def test_slides_template_library_is_reserved_from_materials(self) -> None:
        materials = self.root / "Inbox" / "research-slides" / "experiment"
        materials.mkdir(parents=True)
        (materials / "brief.md").write_text("sample", encoding="utf-8")
        library = self.root / "Inbox" / web_app.SLIDES_TEMPLATE_LIBRARY
        library.mkdir(parents=True)
        (library / "academic.pptx").write_bytes(b"template")
        self.assertEqual(["experiment"], web_app._local_inbox_items("research-slides"))
        with self.assertRaises((ValueError, FileNotFoundError)):
            web_app._resolve_local_inbox_item("research-slides", "../Templates")

    def test_local_inbox_rejects_escape(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(ValueError, "escapes"):
            web_app._resolve_local_inbox_item("research-note", "../../outside")

    def test_endpoint_rejects_icloud_file_for_folder_task(self) -> None:
        loose_file = web_app.settings.icloud_inbox_root / "research-slides" / "loose.txt"
        loose_file.write_text("not a folder", encoding="utf-8")
        with TestClient(web_app.app) as client:
            response = client.post(
                "/api/jobs",
                data={
                    "task": "research-slides",
                    "icloud_item": "loose.txt",
                    "instructions": "Make slides",
                },
            )
        self.assertEqual(400, response.status_code)
        self.assertIn("material folder", response.json()["detail"])

    def test_note_attachments_are_copied_only_to_local_vault(self) -> None:
        job_root = web_app.settings.local_jobs / "attachment-job"
        (job_root / "input" / "materials" / "figures").mkdir(parents=True)
        (job_root / "temp").mkdir()
        (job_root / "output").mkdir()
        (job_root / "input" / "materials" / "figures" / "linear.gif").write_bytes(b"GIF89a")
        (job_root / "input" / "materials" / "notes.txt").write_text("text", encoding="utf-8")
        job = web_app.JobWorkspace(job_root)
        (job_root / "job.json").write_text(json.dumps({
            "task": "research-note", "note_target": "notes/Research/test.md",
            "note_mode": "create", "note_preview": "Before\n\n![[materials/figures/linear.gif]]\n\nAfter",
        }), encoding="utf-8")
        state = save_local(job, web_app.settings)
        self.assertEqual(
            ["notes/_attachments/Research-Starter/attachment-job/materials/figures/linear.gif"],
            state["note_attachments"],
        )
        copied = web_app.settings.local_obsidian_vault / state["note_attachments"][0]
        self.assertEqual(b"GIF89a", copied.read_bytes())
        self.assertFalse((web_app.settings.obsidian_write_root / "_attachments").exists())

    def make_renderable_job(self, job_id: str, task: str) -> Path:
        root = web_app.settings.local_jobs / job_id
        for name in ("input", "temp", "output"):
            (root / name).mkdir(parents=True, exist_ok=True)
        (root / "job.json").write_text(
            json.dumps({
                "job_id": job_id,
                "task": task,
                "status": "completed",
                "stage": "completed",
                "outputs": [],
                "final_response": "done",
            }),
            encoding="utf-8",
        )
        return root

    def test_result_pages_render_only_task_specific_actions(self) -> None:
        self.make_renderable_job("paper", "paper-guide")
        self.make_renderable_job("note", "research-note")
        self.make_renderable_job("slides", "research-slides")
        with TestClient(web_app.app) as client:
            paper = client.get("/jobs/paper").text
            note = client.get("/jobs/note").text
            slides = client.get("/jobs/slides").text
        self.assertIn('id="paper-chat"', paper)
        self.assertIn('id="pdf-viewer"', paper)
        self.assertNotIn('id="save-note"', paper)
        self.assertIn('id="save-note"', note)
        self.assertIn('id="markdown-preview"', note)
        self.assertNotIn('id="paper-chat"', note)
        self.assertNotIn('id="save-note"', slides)
        self.assertNotIn('id="paper-chat"', slides)
        self.assertIn('id="pptx-viewer"', slides)

    def test_job_star_and_exact_delete_do_not_touch_siblings(self) -> None:
        self.make_renderable_job("keep", "paper-guide")
        self.make_renderable_job("remove", "paper-guide")
        with TestClient(web_app.app) as client:
            starred = client.post("/api/jobs/keep/star")
            deleted = client.delete("/api/jobs/remove")
        self.assertTrue(starred.json()["starred"])
        self.assertEqual(200, deleted.status_code)
        self.assertTrue((web_app.settings.local_jobs / "keep" / "job.json").is_file())
        self.assertFalse((web_app.settings.local_jobs / "remove").exists())

    def test_job_title_can_be_renamed_safely(self) -> None:
        self.make_renderable_job("rename", "paper-guide")
        with TestClient(web_app.app) as client:
            response = client.post("/api/jobs/rename/title", data={"title": "  中文 项目标题  "})
            rejected = client.post("/api/jobs/rename/title", data={"title": "x" * 41})
        self.assertEqual("中文 项目标题", response.json()["title"])
        self.assertEqual(400, rejected.status_code)

    def test_job_input_is_available_inline(self) -> None:
        root = self.make_renderable_job("reader", "paper-guide")
        source = root / "input" / "paper.pdf"
        source.write_bytes(b"%PDF-test")
        with TestClient(web_app.app) as client:
            response = client.get("/jobs/reader/input/paper.pdf")
            state = client.get("/api/jobs/reader").json()
        self.assertEqual(200, response.status_code)
        self.assertEqual("inline; filename=\"paper.pdf\"", response.headers["content-disposition"])
        self.assertEqual("paper.pdf", state["paper_file"])

    def test_save_note_is_mechanical_and_local(self) -> None:
        root = self.make_renderable_job("save-with-media", "research-note")
        media = root / "input" / "materials" / "animation.gif"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"GIF89a")
        job = web_app.JobWorkspace(root)
        job.update(
            note_target="notes/Research/test.md", note_mode="create",
            note_preview="## Result\n\n![[materials/animation.gif]]",
        )
        asyncio.run(web_app._save_note_local(job))
        state = job.read()
        expected = "notes/_attachments/Research-Starter/save-with-media/materials/animation.gif"
        self.assertTrue(state["note_local_saved"])
        self.assertEqual("completed", state["note_save_status"])
        self.assertEqual([expected], state["note_attachments"])
        self.assertIn(f"![[{expected}]]", Path(state["note_local_path"]).read_text(encoding="utf-8"))
        self.assertFalse((web_app.settings.obsidian_write_root / "Research" / "test.md").exists())

    def test_same_name_note_is_saved_as_independent_language_version(self) -> None:
        web_app.initialize_local_vault(web_app.settings)
        existing = web_app.settings.local_obsidian_vault / "notes/Research/polarization.md"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("中文旧笔记\n", encoding="utf-8")
        root = self.make_renderable_job("english-version", "research-note")
        job = web_app.JobWorkspace(root)
        job.update(
            language="en", note_target="notes/Research/polarization.md",
            note_mode="append", note_preview="# Polarization\n\nEnglish only.",
        )
        state = save_local(job, web_app.settings)
        saved = Path(state["note_local_path"])
        self.assertEqual("polarization-en.md", saved.name)
        self.assertEqual("中文旧笔记\n", existing.read_text(encoding="utf-8"))
        self.assertEqual("# Polarization\n\nEnglish only.\n", saved.read_text(encoding="utf-8"))
        self.assertEqual("# Polarization\n\nEnglish only.", state["note_preview"])
        self.assertEqual("create", state["note_mode"])

    def test_slides_rejects_new_template_until_it_is_loaded(self) -> None:
        with TestClient(web_app.app) as client:
            response = client.post(
                "/api/jobs",
                data={"task": "research-slides", "instructions": "Make slides"},
                files=[
                    ("files", ("materials/source.txt", b"source", "text/plain")),
                    ("ppt_template", ("academic.pptx", b"pptx-template", "application/vnd.openxmlformats-officedocument.presentationml.presentation")),
                ],
            )
        self.assertEqual(400, response.status_code)
        self.assertIn("先通过", response.json()["detail"])

    def test_template_analysis_is_an_independent_job(self) -> None:
        with TestClient(web_app.app) as client:
            response = client.post(
                "/api/templates/analyze",
                files=[("ppt_template", ("academic.pptx", b"pptx-template", "application/vnd.openxmlformats-officedocument.presentationml.presentation"))],
            )
        self.assertEqual(202, response.status_code)
        state = json.loads(
            (web_app.settings.local_jobs / response.json()["job_id"] / "job.json").read_text(encoding="utf-8")
        )
        self.assertEqual("template-analysis", state["task"])
        self.assertEqual("academic.pptx", state["template_library_item"])
        self.assertEqual("模板载入：academic", state["title"])

    def test_slides_can_copy_existing_template_library_item(self) -> None:
        library = self.root / "Inbox" / web_app.SLIDES_TEMPLATE_LIBRARY
        library.mkdir(parents=True)
        (library / "reusable.pptx").write_bytes(b"reusable-template")
        self.install_template_profile(library / "reusable.pptx")
        with TestClient(web_app.app) as client:
            page = client.get("/tasks/research-slides")
            preview = client.get("/api/templates/file/reusable.pptx")
            response = client.post(
                "/api/jobs",
                data={"task": "research-slides", "instructions": "", "template_item": "reusable.pptx"},
                files=[("files", ("materials/source.txt", b"source", "text/plain"))],
            )
        self.assertIn("reusable.pptx", page.text)
        self.assertIn('class="slides-setup-grid"', page.text)
        self.assertIn('id="template-provider"', page.text)
        self.assertIn('id="template-model"', page.text)
        self.assertIn('id="template-effort"', page.text)
        self.assertIn("内容 / 页面逻辑（可选）", page.text)
        self.assertIn('id="template-drop-zone"', page.text)
        self.assertIn('id="template-pptx-viewer"', page.text)
        self.assertEqual(200, preview.status_code)
        self.assertEqual(b"reusable-template", preview.content)
        self.assertNotIn('name="instructions" required', page.text)
        self.assertEqual(202, response.status_code)
        state = json.loads((web_app.settings.local_jobs / response.json()["job_id"] / "job.json").read_text(encoding="utf-8"))
        self.assertEqual("reusable.pptx", state["template_library_item"])
        self.assertEqual(b"reusable-template", Path(state["template_path"]).read_bytes())
        self.assertTrue(Path(state["template_profile_json"]).is_file())

    def test_task_model_controls_share_usage_and_english_effort_labels(self) -> None:
        with TestClient(web_app.app) as client:
            paper = client.get("/tasks/paper-guide")
            note = client.get("/tasks/research-note")
            slides = client.get("/tasks/research-slides")
        for page in (paper, note):
            self.assertIn('class="standard-task-form"', page.text)
            self.assertIn('class="standard-setup-grid"', page.text)
            self.assertIn('class="standard-controls-column"', page.text)
            self.assertIn('class="primary-task-submit"', page.text)
        self.assertIn('id="template-usage"', slides.text)
        self.assertIn('class="primary-task-submit" type="submit">生成 PPT', slides.text)
        self.assertIn("none:'None'", slides.text)
        self.assertIn("medium:'Medium'", slides.text)
        self.assertIn("ultra:'Ultra'", slides.text)
        session_controls = (
            Path(__file__).parents[1] / "web" / "static" / "session-controls.js"
        ).read_text(encoding="utf-8")
        self.assertIn("none:'None'", session_controls)
        self.assertIn("ultra:'Ultra'", session_controls)
        self.assertNotIn("关闭思考", session_controls)

    def test_loaded_profile_is_associated_by_template_filename(self) -> None:
        library = self.root / "Inbox" / web_app.SLIDES_TEMPLATE_LIBRARY
        library.mkdir(parents=True)
        template = library / "changing.pptx"
        template.write_bytes(b"version-one")
        self.install_template_profile(template)
        template.write_bytes(b"version-two")
        with TestClient(web_app.app) as client:
            response = client.post(
                "/api/jobs",
                data={"task": "research-slides", "template_item": template.name},
                files=[("files", ("materials/source.txt", b"source", "text/plain"))],
            )
        self.assertEqual(202, response.status_code)
        state = json.loads(
            (web_app.settings.local_jobs / response.json()["job_id"] / "job.json").read_text(encoding="utf-8")
        )
        self.assertEqual(template.name, state["template_library_item"])

    def test_slides_prompt_uses_template_as_layout_library(self) -> None:
        root = self.make_renderable_job("slides-template-prompt", "research-slides")
        job = web_app.JobWorkspace(root)
        template = root / "template" / "academic.pptx"
        template.parent.mkdir()
        template.write_bytes(b"fixture")
        profile = root / "template-profile"
        profile.mkdir()
        job.update(template_path=str(template), template_profile_path=str(profile))
        prompt = runner_tasks._skill_prompt("research-slides", job, "", web_app.settings, "zh")
        self.assertIn("layout and visual library", prompt)
        self.assertIn("authoritative page catalogue", prompt)
        self.assertIn("Do not render or visually re-analyse all template pages", prompt)
        self.assertIn("remove every unused template slide", prompt)
        self.assertIn("every editable slide title", prompt)
        self.assertIn("calculation you can reproduce", prompt)
        self.assertIn("language-consistency review", prompt)
        self.assertNotIn("Preserve every existing template slide", prompt)
        self.assertNotIn("append_to_template.py", prompt)

    def test_paper_prompt_requires_direct_conversation_response(self) -> None:
        root = self.make_renderable_job("paper-prompt", "paper-guide")
        prompt = runner_tasks._skill_prompt(
            "paper-guide", web_app.JobWorkspace(root), "", web_app.settings, "zh"
        )
        self.assertIn("directly in your final response", prompt)
        self.assertIn("Do not create reading-guide.md", prompt)
        self.assertNotIn("Save the reading guide", prompt)

    def test_job_records_selected_model_effort_and_language(self) -> None:
        original_status = web_app._get_codex_status

        async def fake_status(*, refresh=False):
            return {
                "models": {"data": [{
                    "model": "test-model",
                    "hidden": False,
                    "supportedReasoningEfforts": [{"reasoningEffort": "high"}],
                }]},
                "usage": {"rateLimits": {}},
            }

        web_app._get_codex_status = fake_status
        try:
            with TestClient(web_app.app) as client:
                response = client.post(
                    "/api/jobs",
                    data={
                        "task": "research-note",
                        "model": "test-model",
                        "effort": "high",
                        "language": "ja",
                    },
                    files=[("files", ("materials/a.txt", b"A", "text/plain"))],
                )
        finally:
            web_app._get_codex_status = original_status
        self.assertEqual(202, response.status_code)
        state = json.loads(
            (web_app.settings.local_jobs / response.json()["job_id"] / "job.json").read_text(encoding="utf-8")
        )
        self.assertEqual("test-model", state["model"])
        self.assertEqual("high", state["reasoning_effort"])
        self.assertEqual("ja", state["language"])

    def test_all_task_types_reach_runner_before_using_result(self) -> None:
        original_runner = runner_tasks.CodexRunner

        class FakeRunner:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def run_skill(self, **kwargs):
                response = "first response"
                if kwargs["skill_name"] == "research-note":
                    response = "<research-note-target>notes/test.md</research-note-target>\n<research-note-mode>create</research-note-mode>\n```markdown\nfirst response\n```"
                return "thread-test", type("FakeResult", (), {"final_response": response + "\n<research-starter-title>中文测试标题</research-starter-title>"})()

        runner_tasks.CodexRunner = FakeRunner
        try:
            for task in ("paper-guide", "research-note", "research-slides"):
                root = self.make_renderable_job(f"runner-{task}", task)
                job = web_app.JobWorkspace(root)
                asyncio.run(runner_tasks.run_existing_job(job, "test", settings=web_app.settings))
                state = job.read()
                self.assertEqual("completed", state["status"])
                self.assertIn("first response", state["initial_response"])
                if task == "research-note":
                    self.assertEqual("first response", state["note_preview"])
                self.assertEqual("中文测试标题", state["title"])
                self.assertEqual("thread-test", state["thread_id"])
        finally:
            runner_tasks.CodexRunner = original_runner


if __name__ == "__main__":
    unittest.main()
