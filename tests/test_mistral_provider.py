"""Offline tests for Mistral; no live inference is sent."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from omni.cli import main
from omni.executor import MistralAPIProvider, ManualProvider, provider_from_env
from omni.models import Brief


def brief() -> Brief:
    return Brief(
        task_id="t-mistral",
        agent_id="omni-research",
        specialty="research",
        objective="Summarize the supplied material",
        acceptance_criteria=["summary_present", "sources_cited"],
        allowed_tools=[],
        boundaries=["Do not claim external research was performed"],
    )


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit=-1):
        return self.payload


class TestMistralProvider(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key_file = Path(self.tmp.name) / "mistral.key"
        self.key_file.write_text("test-secret-key", encoding="utf-8")
        if os.name != "nt":
            self.key_file.chmod(0o600)
        self.env = mock.patch.dict(os.environ, {
            "MISTRAL_API_KEY_FILE": str(self.key_file),
            "OMNI_PROVIDER": "mistral",
        }, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_availability_is_local_and_does_not_send_a_request(self):
        provider = MistralAPIProvider()
        with mock.patch("urllib.request.urlopen") as send:
            ok, detail = provider.available()
        self.assertTrue(ok)
        self.assertIn("no API request", detail)
        send.assert_not_called()

    def test_rejects_group_or_world_readable_key_file(self):
        if os.name == "nt":
            self.skipTest("POSIX permission check")
        self.key_file.chmod(0o644)
        ok, detail = MistralAPIProvider().available()
        self.assertFalse(ok)
        self.assertIn("not private", detail)

    def test_rejects_symlink_key_file(self):
        link = Path(self.tmp.name) / "key-link"
        link.symlink_to(self.key_file)
        os.environ["MISTRAL_API_KEY_FILE"] = str(link)
        ok, _ = MistralAPIProvider().available()
        self.assertFalse(ok)

    def test_real_request_shape_and_structured_response_are_handled(self):
        payload = {
            "id": "req-test-123",
            "model": "mistral-small-latest",
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "summary": "A concise result",
                        "evidence": ["The supplied brief was processed"],
                        "met_criteria": ["summary_present", "not-a-real-criterion"],
                        "artifacts": [],
                        "claims": {"kind": "summary"},
                    })
                }
            }],
        }

        def fake_send(request, timeout):
            self.assertEqual(request.full_url, "https://api.mistral.ai/v1/chat/completions")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-secret-key")
            self.assertEqual(timeout, 120)
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(body["model"], "mistral-small-latest")
            self.assertEqual(body["response_format"], {"type": "json_object"})
            return FakeResponse(payload)

        with mock.patch("urllib.request.urlopen", side_effect=fake_send):
            result = MistralAPIProvider().execute(brief())
        self.assertTrue(result.executed)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.met_criteria, ["summary_present"])
        self.assertIn("mistral_request_id=req-test-123", result.evidence)
        self.assertNotIn("test-secret-key", str(result.to_dict()))

    def test_http_errors_do_not_echo_response_body_or_key(self):
        def fail(*_args, **_kwargs):
            raise HTTPError("https://api.mistral.ai/v1/chat/completions", 401, "bad", {}, None)

        with mock.patch("urllib.request.urlopen", side_effect=fail):
            result = MistralAPIProvider().execute(brief())
        self.assertEqual(result.status, "failed")
        self.assertIn("authentication failed", result.error)
        self.assertNotIn("test-secret-key", result.error)

    def test_invalid_json_contract_is_incomplete_not_success(self):
        payload = {
            "id": "req-invalid",
            "model": "mistral-small-latest",
            "choices": [{"message": {"content": "not-json"}}],
        }
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
            result = MistralAPIProvider().execute(brief())
        self.assertTrue(result.executed)
        self.assertEqual(result.status, "incomplete")

    def test_cli_verify_is_local_only(self):
        output = StringIO()
        with redirect_stdout(output), mock.patch("urllib.request.urlopen") as send:
            code = main(["providers", "--verify", "mistral"])
        self.assertEqual(code, 0)
        self.assertIn("no API request", output.getvalue())
        send.assert_not_called()

    def test_provider_selection_is_explicit(self):
        provider, _ = provider_from_env()
        self.assertIsInstance(provider, MistralAPIProvider)

    def test_missing_key_never_falls_back_to_a_fake_provider(self):
        os.environ.pop("MISTRAL_API_KEY_FILE")
        provider, detail = provider_from_env()
        self.assertIsInstance(provider, ManualProvider)
        self.assertIn("unavailable", detail)


if __name__ == "__main__":
    unittest.main()
