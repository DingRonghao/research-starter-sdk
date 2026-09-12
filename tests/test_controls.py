import asyncio
from dataclasses import replace
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


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        paths = {key: self.root / key for key in (
            'local_jobs', 'local_fallback_output', 'icloud_inbox_root', 'icloud_output_root', 'codex_home', 'obsidian_vault', 'local_obsidian_vault')}
        paths['obsidian_write_root'] = paths['obsidian_vault'] / 'notes'
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        paths['base_python'] = self.root / 'Python.exe'
        paths['base_python'].write_bytes(b'test fixture')
        paths['obsidian_exe'] = self.root / 'Obsidian.exe'
        paths['obsidian_exe'].write_bytes(b'test fixture')
        self.settings = replace(web.settings, project_root=self.root, **paths)
        self.config = self.root / 'config.local.json'
        self.config.write_text(json.dumps({'project_root': '.', 'base_python': str(self.settings.base_python), **{k: str(v) for k,v in paths.items()}}), encoding='utf-8')

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

    def test_settings_change_is_used_immediately(self):
        changed_jobs = self.root / 'changed-jobs'
        changed_jobs.mkdir()
        with patch.object(web, 'settings', self.settings), TestClient(web.app) as client:
            response = client.post('/api/settings', json={'local_jobs': str(changed_jobs)})
            self.assertEqual(200, response.status_code)
            self.assertEqual(changed_jobs, web.settings.local_jobs)
        saved = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual('changed-jobs', saved['local_jobs'])

    def test_launcher_reads_base_python_from_config(self):
        launcher = (Path(__file__).parents[1] / 'Start Research Starter.cmd').read_text(encoding='utf-8')
        self.assertIn('.base_python', launcher)
        self.assertIn('Bootstrap Research Starter.ps1', launcher)
        self.assertIn('.npm_cmd', launcher)
        self.assertNotIn('C:\\mambaforge', launcher)

    def test_first_run_bootstrap_is_shipped_and_uses_file_picker(self):
        script = (Path(__file__).parents[1] / 'Bootstrap Research Starter.ps1').read_text(encoding='utf-8')
        self.assertIn('OpenFileDialog', script)
        self.assertIn('Python 3.10, 3.11, or 3.12', script)
        self.assertIn('Node.js 18 or newer', script)
        self.assertNotRegex(script, r'[\u0080-\uffff]')

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
