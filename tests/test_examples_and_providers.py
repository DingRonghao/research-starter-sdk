import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from runner.config import load_settings
from runner.examples import EXAMPLES, seed_completed_examples
from runner.model_providers import (
    delete_deepseek_key, deepseek_configured, load_deepseek_key,
    delete_provider_key, load_provider_key, provider_configured, provider_overrides,
    provider_spec, save_deepseek_key, save_provider_key,
)


class ExamplesAndProvidersTests(unittest.TestCase):
    def test_examples_seed_once_and_include_complete_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = load_settings()
            settings = replace(base, project_root=root, local_jobs=root / ".runtime/jobs")
            for task in ("paper-guide", "research-note", "research-slides"):
                inbox = root / "Inbox" / task / "public-sample"
                output = root / "Output" / task / "public-sample"
                inbox.mkdir(parents=True)
                output.mkdir(parents=True)
                (inbox / "source.txt").write_text("source", encoding="utf-8")
                (output / "README.md").write_text("completed example", encoding="utf-8")
            (root / "Output/research-note/public-sample/example-note.md").write_text("# note", encoding="utf-8")
            (root / "Output/research-slides/public-sample/temperature-scan-example.pptx").write_bytes(b"sample")
            created = seed_completed_examples(settings)
            self.assertEqual(set(EXAMPLES), set(created))
            self.assertEqual([], seed_completed_examples(settings))
            for job_id in EXAMPLES:
                state = __import__('json').loads((settings.local_jobs / job_id / "job.json").read_text(encoding="utf-8"))
                self.assertEqual("completed", state["status"])
                self.assertTrue(state["is_example"])
            slides = __import__('json').loads((settings.local_jobs / "example-research-slides/job.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(slides["outputs"]))

    def test_deepseek_key_is_encrypted_and_provider_does_not_require_openai_auth(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = "sk-test-secret-value"
            encrypted = b"windows-dpapi-ciphertext"
            with patch("runner.model_providers.win32crypt.CryptProtectData", return_value=encrypted), \
                 patch("runner.model_providers.win32crypt.CryptUnprotectData", return_value=("", secret.encode())):
                save_deepseek_key(root, secret)
                self.assertTrue(deepseek_configured(root))
                self.assertEqual(secret, load_deepseek_key(root))
                self.assertEqual(encrypted, (root / ".runtime/secrets/deepseek-api-key.bin").read_bytes())
            overrides = provider_overrides("deepseek", root)
            self.assertIn("model_providers.deepseek.requires_openai_auth=false", overrides)
            self.assertIn('model_reasoning_effort="high"', overrides)
            self.assertTrue(any(item.startswith("model_catalog_json=") for item in overrides))
            self.assertTrue(delete_deepseek_key(root))
            self.assertFalse(deepseek_configured(root))

    def test_kimi_k3_uses_native_responses_without_openai_auth(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = "kimi-test-secret-value"
            encrypted = b"windows-dpapi-kimi-ciphertext"
            with patch("runner.model_providers.win32crypt.CryptProtectData", return_value=encrypted), \
                 patch("runner.model_providers.win32crypt.CryptUnprotectData", return_value=("", secret.encode())):
                save_provider_key(root, "kimi", secret)
                self.assertTrue(provider_configured(root, "kimi"))
                self.assertEqual(secret, load_provider_key(root, "kimi"))
                self.assertEqual(encrypted, (root / ".runtime/secrets/kimi-api-key.bin").read_bytes())
            spec = provider_spec("kimi")
            self.assertEqual("kimi-k3", spec.model)
            self.assertEqual(("low", "high", "max"), spec.reasoning_efforts)
            self.assertNotIn("none", spec.reasoning_efforts)
            overrides = provider_overrides("kimi", root)
            self.assertIn('model_providers.kimi.wire_api="responses"', overrides)
            self.assertIn("model_providers.kimi.requires_openai_auth=false", overrides)
            self.assertIn('model_providers.kimi.base_url="https://api.moonshot.ai/v1"', overrides)
            self.assertIn("model_context_window=1048576", overrides)
            self.assertTrue(any("kimi-models.json" in item for item in overrides))
            self.assertTrue(delete_provider_key(root, "kimi"))
            self.assertFalse(provider_configured(root, "kimi"))


if __name__ == "__main__":
    unittest.main()
