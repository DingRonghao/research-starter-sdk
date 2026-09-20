import asyncio
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient
import web.app as web
from runner.jobs import create_job
from runner.login import LoginManager
from runner.preferences import save_preferences
from runner.tasks import resume_job
from runner.note_store import open_local, publish_cloud, save_local
from runner.instance import instance_info, preferred_ports, select_port
from web.pptx_preview import normalized_pptx_bytes


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        paths = {key: self.root / key for key in (
            'local_jobs', 'local_fallback_output', 'icloud_inbox_root', 'icloud_output_root', 'codex_home', 'obsidian_vault', 'local_obsidian_vault')}
        paths['obsidian_write_root'] = paths['obsidian_vault'] / 'notes'
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        paths['obsidian_exe'] = self.root / 'Obsidian.exe'
        paths['obsidian_exe'].write_bytes(b'test fixture')
        self.settings = replace(web.settings, project_root=self.root, **paths)
        self.config = self.root / 'config.local.json'
        self.config.write_text(json.dumps({'project_root': '.', **{k: str(v) for k,v in paths.items()}}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_settings_backup_and_persistence(self):
        original = self.config.read_bytes()
        changed = self.settings.obsidian_vault / 'new-notes'
        changed.mkdir()
        updated = save_preferences(self.settings, {'obsidian_write_root': str(changed)})
        self.assertEqual(changed, updated.obsidian_write_root)
        self.assertEqual(original, next((self.root / '.runtime/config-backups').glob('*/config.local.json')).read_bytes())
        self.assertFalse((self.root / 'app-info.json').exists())

    def test_invalid_settings_do_not_modify_config(self):
        before = self.config.read_bytes()
        for values in ({'obsidian_write_root': str(self.root)}, {'local_jobs': str(self.root.parent)}, {'github_url': 'javascript:alert(1)'}, {'codex_home': ''}):
            with self.assertRaises(ValueError):
                save_preferences(self.settings, values)
            self.assertEqual(before, self.config.read_bytes())

    def test_optional_cloud_paths_can_be_disabled(self):
        updated = save_preferences(self.settings, {
            'icloud_inbox_root': '', 'icloud_output_root': '',
            'obsidian_vault': '', 'obsidian_write_root': '',
        })
        self.assertIsNone(updated.icloud_inbox_root)
        self.assertIsNone(updated.icloud_output_root)
        self.assertIsNone(updated.obsidian_vault)
        self.assertIsNone(updated.obsidian_write_root)
        saved = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual('', saved['icloud_inbox_root'])
        self.assertEqual('', saved['obsidian_write_root'])
        reloaded = __import__('runner.config', fromlist=['load_settings']).load_settings(self.config)
        self.assertIsNone(reloaded.icloud_inbox_root)
        self.assertIsNone(reloaded.obsidian_write_root)

    def test_windows_powershell_bom_config_is_accepted(self):
        data = json.loads(self.config.read_text(encoding='utf-8'))
        self.config.write_text(json.dumps(data), encoding='utf-8-sig')
        reloaded = __import__('runner.config', fromlist=['load_settings']).load_settings(self.config)
        self.assertEqual(self.settings.local_jobs, reloaded.local_jobs)
        updated = save_preferences(reloaded, {})
        self.assertEqual(self.settings.local_jobs, updated.local_jobs)

    def test_settings_change_is_used_immediately(self):
        changed_jobs = self.root / 'changed-jobs'
        changed_jobs.mkdir()
        with patch.object(web, 'settings', self.settings), TestClient(web.app) as client:
            response = client.post('/api/settings', json={'local_jobs': str(changed_jobs)})
            self.assertEqual(200, response.status_code)
            self.assertEqual(changed_jobs, web.settings.local_jobs)
        saved = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual('changed-jobs', saved['local_jobs'])

    def test_launcher_uses_only_bundled_runtimes(self):
        launcher = (Path(__file__).parents[1] / 'Start Research Starter.cmd').read_text(encoding='utf-8')
        self.assertIn('runtime\\python\\python.exe', launcher)
        self.assertIn('runtime\\node\\node.exe', launcher)
        self.assertIn('Start-Process', launcher)
        self.assertIn('-WindowStyle Hidden', launcher)
        self.assertNotIn('pythonw.exe', launcher)
        self.assertNotIn('start "" /b "%PROJECT_PYTHON%"', launcher)
        self.assertNotIn('pip install', launcher)
        self.assertNotIn('npm', launcher.lower())
        self.assertNotIn('Bootstrap Research Starter.ps1', launcher)
        self.assertNotIn('C:\\mambaforge', launcher)

    def test_brand_icons_and_portable_launcher_builder_are_present(self):
        project = Path(__file__).parents[1]
        self.assertTrue((project / 'web/static/app-icon.png').is_file())
        self.assertTrue((project / 'web/static/favicon.ico').is_file())
        self.assertTrue((project / 'assets/app-icon.ico').is_file())
        base = (project / 'web/templates/base.html').read_text(encoding='utf-8')
        self.assertIn('/static/favicon.ico', base)
        self.assertIn('/static/app-icon.png', base)
        build = (project / 'tools/Build Windows Release.ps1').read_text(encoding='utf-8')
        self.assertIn('ResearchStarterLauncher.cs', build)
        self.assertIn('/target:winexe', build)
        self.assertIn('-CertificateThumbprint', build)
        self.assertIn('$RequireSignature', build)
        self.assertIn('signtool.exe', build)
        self.assertIn('/XD .git .runtime .venv runtime node_modules Inbox Output', build)
        self.assertIn("$sampleSource = Join-Path $project \"$area\\$task\\public-sample\"", build)
        self.assertIn("$publicTemplateName = 'Academic-Research-Presentation.pptx'", build)
        self.assertIn(".research-starter-analysis\\$publicTemplateName", build)
        self.assertIn("@('profile.json', 'profile.md')", build)
        launcher_source = (project / 'tools/ResearchStarterLauncher.cs').read_text(encoding='utf-8')
        self.assertIn('AppDomain.CurrentDomain.BaseDirectory', launcher_source)
        self.assertIn('CreateNoWindow = true', launcher_source)

    def test_pptx_preview_renders_complete_slides_inside_its_scroll_container(self):
        root = Path(__file__).parents[1]
        script = (root / 'web/static/job.js').read_text(encoding='utf-8')
        preview = (root / 'web/static/pptx-preview.js').read_text(encoding='utf-8')
        self.assertEqual('0.4.1.8', web.ASSET_VERSION)
        self.assertIn('openPptxPreview(container,buffer)', script)
        self.assertIn('scrollContainer: container', preview)
        self.assertIn('listOptions: {windowed: false', preview)
        self.assertIn('lazySlides: false', preview)
        self.assertIn('lazyMedia: false', preview)
        self.assertIn('correctPptxThemeBackgrounds(viewer, container)', preview)
        self.assertIn("viewer.addEventListener('rendercomplete'", preview)
        server_preview = (root / 'web/pptx_preview.py').read_text(encoding='utf-8')
        self.assertIn('?preview=true', script)
        self.assertIn('ppt/slides/charts', server_preview)
        self.assertIn('ppt/media/', server_preview)
        self.assertIn('.svg', server_preview)
        self.assertNotIn('content.style.zoom', (root / 'web/templates/task.html').read_text(encoding='utf-8'))
        self.assertIn("master.colorMap.get(scheme)", preview)

    def test_pptx_preview_copy_strips_xml_bom_without_changing_source(self):
        source = self.root / "bom.pptx"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("[Content_Types].xml", b"\xef\xbb\xbf<Types/>")
            archive.writestr("ppt/slides/slide1.xml", b"\xef\xbb\xbf<p:sld/>")
        original = source.read_bytes()
        normalized = normalized_pptx_bytes(source)
        with zipfile.ZipFile(BytesIO(normalized)) as archive:
            self.assertEqual(b"<Types/>", archive.read("[Content_Types].xml"))
            self.assertEqual(b"<p:sld/>", archive.read("ppt/slides/slide1.xml"))
        self.assertEqual(original, source.read_bytes())

    def test_development_and_release_instances_use_separate_port_ranges(self):
        (self.root / '.git').mkdir()
        development = instance_info(self.root)
        release_root = self.root / 'release-copy'
        release_root.mkdir()
        release = instance_info(release_root)
        self.assertEqual('development', development.channel)
        self.assertEqual(8765, preferred_ports(development)[0])
        self.assertEqual('release', release.channel)
        self.assertGreaterEqual(preferred_ports(release)[0], 8800)
        self.assertNotEqual(development.instance_id, release.instance_id)

    def test_launcher_never_reuses_a_foreign_instance(self):
        info = instance_info(self.root)
        with patch('runner.instance.probe_instance', return_value=False), \
             patch('runner.instance.port_is_free', side_effect=[False, True]):
            port, running = select_port(info)
        self.assertEqual(preferred_ports(info)[1], port)
        self.assertFalse(running)

    def test_runtime_paths_are_fixed_and_not_editable_preferences(self):
        self.assertEqual(self.root / 'runtime/python/python.exe', self.settings.python_exe)
        self.assertEqual(self.root / 'runtime/node/node.exe', self.settings.node_exe)
        self.assertNotIn('base_python', __import__('runner.preferences', fromlist=['PATH_LABELS']).PATH_LABELS)
        self.assertNotIn('node_exe', __import__('runner.preferences', fromlist=['PATH_LABELS']).PATH_LABELS)

    def test_release_defaults_work_without_local_config(self):
        release = self.root / 'release-defaults'
        release.mkdir()
        (release / 'config.example.json').write_text(json.dumps({
            'project_root': '.', 'local_jobs': '.runtime/jobs',
            'local_fallback_output': '.runtime/local-output', 'codex_home': '',
            'local_obsidian_vault': '.runtime/obsidian-local-vault',
        }), encoding='utf-8')
        loaded = __import__('runner.config', fromlist=['load_settings']).load_settings(release / 'config.local.json')
        self.assertTrue(loaded.local_jobs.is_dir())
        self.assertTrue(loaded.local_fallback_output.is_dir())
        self.assertTrue(loaded.local_obsidian_vault.is_dir())
        self.assertEqual(Path.home() / '.codex', loaded.codex_home)

    def test_busy_job_prevents_settings_change(self):
        create_job(self.settings.local_jobs, 'paper-guide', [])
        with patch.object(web, 'settings', self.settings), TestClient(web.app) as client:
            response = client.post('/api/settings', json={})
        self.assertEqual(409, response.status_code)

    def test_cross_origin_cannot_write_settings(self):
        with TestClient(web.app) as client:
            response = client.post('/api/settings', json={}, headers={'Origin': 'https://unrelated.example'})
        self.assertEqual(403, response.status_code)

    def test_followup_uses_selected_model_and_reuses_thread(self):
        job = create_job(self.settings.local_jobs, 'paper-guide', [])
        job.update(status='completed', thread_id='existing-thread', model='old-model', reasoning_effort='low')
        calls = []
        async def validate(model, effort):
            self.assertEqual(('new-model', 'high'), (model, effort))
        class Runner:
            def __init__(self, *args): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def run_skill(self, **kwargs):
                calls.append(kwargs)
                return 'existing-thread', SimpleNamespace(final_response='Answer')
        with patch.object(web, 'settings', self.settings), patch.object(web, '_validate_codex_selection', validate), patch('runner.tasks.CodexRunner', Runner), TestClient(web.app) as client:
            response = client.post(f'/api/jobs/{job.root.name}/follow-up', data={'question':'Explain equation 2', 'model':'new-model', 'effort':'high'})
        self.assertEqual(202, response.status_code)
        self.assertEqual('existing-thread', calls[0]['thread_id'])
        self.assertEqual('new-model', calls[0]['model'])
        self.assertEqual('high', calls[0]['effort'])
        self.assertFalse(calls[0]['include_skill'])
        self.assertIn('existing Docling Markdown/JSON', calls[0]['prompt'])
        self.assertEqual('Answer', job.read()['follow_ups'][0]['response'])

    def test_two_slides_revisions_keep_old_outputs_and_select_latest(self):
        job = create_job(self.settings.local_jobs, 'research-slides', [])
        original = job.output / 'original.pptx'
        original.write_bytes(b'original unchanged')
        job.update(status='completed', thread_id='slides-thread', outputs=[str(original)])
        class Runner:
            def __init__(self, *args): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def run_skill(self, **kwargs):
                path = re.search(r'Save the complete revised deck ONLY at (.+?\.pptx)', kwargs['prompt']).group(1)
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('ppt/presentation.xml', '<presentation/>')
                return 'slides-thread', SimpleNamespace(final_response='Revised')
        with patch('runner.tasks.CodexRunner', Runner):
            for feedback in ('Make concise', 'Enlarge figures'):
                asyncio.run(resume_job(job.root, feedback, self.settings, operation='slides_revision'))
        state = job.read()
        self.assertEqual(2, len(state['slides_revisions']))
        self.assertEqual(3, len(state['outputs']))
        self.assertEqual(b'original unchanged', original.read_bytes())
        presentation = web._present_job(job)
        self.assertEqual(state['latest_pptx'], state['outputs'][presentation['pptx_output_index']])
        versions = presentation['pptx_versions']
        self.assertEqual(['V1 · 初始版本', 'V2 · 第 1 次修订 · Make concise', 'V3 · 第 2 次修订 · Enlarge figures'], [item['label'] for item in versions])
        self.assertFalse(versions[0]['latest'])
        self.assertTrue(versions[-1]['latest'])
        with patch.object(web, 'settings', self.settings), TestClient(web.app) as client:
            response = client.get(f"/jobs/{job.root.name}/output/{versions[-1]['index']}")
        disposition = response.headers['content-disposition']
        self.assertIn('V3-', disposition)
        self.assertNotIn('revision-', disposition)

    def test_login_keeps_client_alive_until_completion(self):
        async def exercise():
            completed = asyncio.Event()
            lifecycle = []
            class Client:
                def __init__(self, *args): pass
                async def __aenter__(self): lifecycle.append('open'); return self
                async def __aexit__(self, *args): lifecycle.append('closed')
                async def login_chatgpt(self):
                    async def wait():
                        await completed.wait()
                        return SimpleNamespace(success=True, error=None)
                    return SimpleNamespace(auth_url='https://auth.openai.com/test', wait=wait)
            with patch('runner.login.AsyncCodex', Client):
                manager = LoginManager()
                result = await manager.start(self.settings)
                self.assertEqual('waiting', result['status'])
                self.assertEqual(['open'], lifecycle)
                completed.set()
                await manager.task
                self.assertEqual('completed', manager.state['status'])
                self.assertEqual(['open', 'closed'], lifecycle)
        asyncio.run(exercise())

    def _local_note_job(self, *, opened=True):
        job = create_job(self.settings.local_jobs, 'research-note', [])
        material = job.input / 'figure.gif'
        material.write_bytes(b'GIF89a-local')
        job.update(
            note_target='notes/Research/test.md', note_mode='create',
            note_preview='## Result\n\n![[figure.gif]]',
        )
        save_local(job, self.settings)
        if opened:
            job.update(note_local_opened=True)
        return job

    def test_local_note_must_be_opened_before_cloud_publish(self):
        job = self._local_note_job(opened=False)
        with self.assertRaisesRegex(ValueError, 'Open the saved local note'):
            publish_cloud(job, self.settings)
        appdata = self.root / 'appdata'
        registry = appdata / 'obsidian/obsidian.json'
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({'vaults': {'cloud-id': {'path': str(self.settings.obsidian_vault)}}}), encoding='utf-8')
        with patch.dict('os.environ', {'APPDATA': str(appdata)}), patch('runner.note_store.subprocess.Popen') as launch:
            state = open_local(job, self.settings)
        self.assertTrue(state['note_local_opened'])
        command = launch.call_args.args[0]
        self.assertEqual(str(self.settings.obsidian_exe), command[0])
        self.assertIn('obsidian://open?vault=', command[1])
        self.assertIn('&file=notes%2FResearch%2Ftest.md', command[1])
        saved = json.loads(registry.read_text(encoding='utf-8'))
        self.assertEqual(2, len(saved['vaults']))
        self.assertTrue(list((self.root / '.runtime/obsidian-config-backups').glob('*-obsidian.json')))

    def test_research_note_local_save_works_without_cloud(self):
        local_only = replace(self.settings, obsidian_vault=None, obsidian_write_root=None)
        job = create_job(local_only.local_jobs, 'research-note', [])
        job.update(
            language='zh', note_target='Notes/Research/local-only.md',
            note_mode='create', note_preview='# 仅本地笔记',
        )
        state = save_local(job, local_only)
        self.assertTrue(Path(state['note_local_path']).is_file())
        self.assertIsNone(state['note_cloud_target'])

    def test_cloud_publish_copies_note_and_attachment_only_into_record(self):
        job = self._local_note_job()
        state = publish_cloud(job, self.settings)
        remote_record = self.settings.obsidian_write_root
        self.assertTrue((remote_record / 'Research/test.md').is_file())
        self.assertEqual(
            b'GIF89a-local',
            (remote_record / '_attachments/Research-Starter' / job.root.name / 'figure.gif').read_bytes(),
        )
        self.assertFalse((self.settings.obsidian_vault / '_attachments').exists())
        self.assertTrue(state['note_cloud_published'])
        self.assertEqual(2, len(state['cloud_outputs']))

    def test_cloud_change_after_local_save_stops_publish(self):
        job = self._local_note_job()
        remote = self.settings.obsidian_write_root / 'Research/test.md'
        remote.parent.mkdir(parents=True, exist_ok=True)
        remote.write_text('changed on another device', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Cloud note changed'):
            publish_cloud(job, self.settings)
        self.assertEqual('changed on another device', remote.read_text(encoding='utf-8'))
