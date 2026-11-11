"""Real subprocess execution and truthful provider detection.

These tests spawn actual processes; nothing here is simulated.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni.executor import (
    ManualProvider,
    SubprocessProvider,
    available_provider_names,
    detect_clis,
    provider_from_env,
)
from omni.models import Brief, ProviderResult, Result


def make_brief() -> Brief:
    return Brief(
        task_id="t1-test",
        agent_id="omni-qa",
        specialty="testing-qa",
        objective="run the suite",
        acceptance_criteria=["tests_run"],
        allowed_tools=["run_tests"],
        boundaries=["no network"],
    )


class TestSubprocessProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_successful_command_is_really_executed(self) -> None:
        provider = SubprocessProvider(
            command=[sys.executable, "-c", "import sys;print('ran', sys.argv[1:])", "{brief_file}"],
            name="python-test",
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertTrue(result.executed)
        self.assertEqual(result.status, "ok")
        self.assertIn("ran", result.summary)
        self.assertIn("exit_code=0", result.evidence)
        self.assertGreater(result.duration_s, 0)

    def test_non_zero_exit_is_a_failure(self) -> None:
        provider = SubprocessProvider(
            command=[sys.executable, "-c", "import sys;print('boom', file=sys.stderr);sys.exit(3)"],
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertTrue(result.executed)
        self.assertEqual(result.status, "failed")
        self.assertIn("3", result.error or "")

    def test_missing_executable_is_reported_not_faked(self) -> None:
        provider = SubprocessProvider(command=["omni-definitely-not-installed"])
        ok, detail = provider.available()
        self.assertFalse(ok)
        self.assertIn("not found", detail)
        result = provider.execute(make_brief(), self.workdir)
        self.assertFalse(result.executed)
        self.assertEqual(result.status, "failed")

    def test_timeout_is_a_failure(self) -> None:
        provider = SubprocessProvider(
            command=[sys.executable, "-c", "import time;time.sleep(5)"], timeout=1
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertEqual(result.status, "failed")
        self.assertIn("timeout", result.error or "")

    def test_prompt_substitution_still_works_and_brief_file_is_removed(self) -> None:
        provider = SubprocessProvider(
            command=[sys.executable, "-c", "import sys;print(len(sys.argv[1])>100)", "{prompt}"]
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertEqual(result.summary.strip(), "True")
        self.assertEqual(list(self.workdir.glob(".omni-brief-*")), [])

    def test_brief_file_is_private_during_execution_and_removed_after(self) -> None:
        provider = SubprocessProvider(
            command=[
                sys.executable,
                "-c",
                "import os,stat,sys; p=sys.argv[1]; print(os.path.isfile(p)); print(oct(stat.S_IMODE(os.stat(p).st_mode)))",
                "{brief_file}",
            ]
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertEqual(result.status, "ok")
        self.assertIn("True", result.summary)
        if os.name != "nt":
            self.assertIn("0o600", result.summary)
        self.assertEqual(list(self.workdir.glob(".omni-brief-*")), [])

    def test_provider_stdout_stderr_and_error_are_redacted(self) -> None:
        github_secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        keyed_secret = "api_key=super-secret-value"
        code = (
            "import sys; "
            f"print({github_secret!r}); "
            f"print({keyed_secret!r}, file=sys.stderr); "
            "sys.exit(4)"
        )
        provider = SubprocessProvider(command=[sys.executable, "-c", code])
        result = provider.execute(make_brief(), self.workdir)
        self.assertEqual(result.status, "failed")
        for secret in (github_secret, keyed_secret):
            self.assertNotIn(secret, result.summary)
            self.assertNotIn(secret, result.stdout)
            self.assertNotIn(secret, result.stderr)
            self.assertNotIn(secret, result.error or "")
        self.assertIn("[REDACTED]", result.summary)
        self.assertIn("[REDACTED]", result.stderr)
        self.assertIn("[REDACTED]", result.error or "")

    def test_custom_provider_payload_is_redacted_at_result_ingestion(self) -> None:
        github_secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        api_secret = "AKIAABCDEFGHIJKLMNOP"
        pr = ProviderResult(
            status="ok",
            summary=github_secret,
            evidence=[api_secret],
            artifacts=[f"artifact:{github_secret}"],
            claims={github_secret: api_secret},
            executed=True,
            provider="custom-provider",
            error=f"failure token={github_secret}",
        )
        result = Result.from_provider(make_brief(), pr)
        for secret in (github_secret, api_secret):
            self.assertNotIn(secret, result.summary)
            self.assertNotIn(secret, str(result.evidence))
            self.assertNotIn(secret, str(result.artifacts))
            self.assertNotIn(secret, str(result.claims))
            self.assertNotIn(secret, result.error or "")
        self.assertIn("[REDACTED]", str(result.claims))


    def test_secrets_are_redacted_before_brief_reaches_subprocess(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        brief = make_brief()
        brief.objective = f"Review this supplied context: {secret}"

        cases = [
            (
                "prompt",
                "import sys; print(sys.argv[1])",
                "{prompt}",
            ),
            (
                "brief_file",
                "import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())",
                "{brief_file}",
            ),
        ]
        for label, code, placeholder in cases:
            with self.subTest(transport=label):
                provider = SubprocessProvider(
                    command=[sys.executable, "-c", code, placeholder]
                )
                result = provider.execute(brief, self.workdir)
                self.assertEqual(result.status, "ok")
                self.assertNotIn(secret, result.stdout)
                self.assertIn("[REDACTED]", result.stdout)
                self.assertEqual(list(self.workdir.glob(".omni-brief-*")), [])


class TestProviderDetection(unittest.TestCase):
    def test_manual_provider_never_claims_execution(self) -> None:
        result = ManualProvider().execute(make_brief())
        self.assertFalse(result.executed)
        self.assertEqual(result.status, "pending_human")
        self.assertIn("No automated provider", result.summary)

    def test_env_without_command_falls_back_to_manual(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            provider, detail = provider_from_env()
        self.assertIsInstance(provider, ManualProvider)
        self.assertIn("OMNI_PROVIDER_CMD", detail)

    def test_env_with_unusable_command_falls_back_to_manual(self) -> None:
        with mock.patch.dict("os.environ", {"OMNI_PROVIDER_CMD": "omni-not-a-real-cli {prompt}"}):
            provider, detail = provider_from_env()
        self.assertIsInstance(provider, ManualProvider)
        self.assertIn("unusable", detail)

    def test_env_with_real_command_builds_subprocess_provider(self) -> None:
        with mock.patch.dict("os.environ", {"OMNI_PROVIDER_CMD": f"{sys.executable} -c pass", "OMNI_PROVIDER_NAME": "py"}):
            provider, _ = provider_from_env()
        self.assertIsInstance(provider, SubprocessProvider)
        self.assertEqual(provider.name, "py")

    def test_detect_clis_reports_availability_truthfully(self) -> None:
        probes = detect_clis()
        self.assertTrue(probes)
        for probe in probes:
            self.assertIn("command", probe)
            self.assertIsInstance(probe["available"], bool)
            if probe["available"]:
                self.assertTrue(probe["path"])
            else:
                self.assertEqual(probe["path"], "")
        available = available_provider_names()
        self.assertEqual(available, [p["command"] for p in probes if p["available"]])


class TestMistralProvider(unittest.TestCase):
    def test_mistral_is_selected_but_paid_inference_is_locked_by_default(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"OMNI_PROVIDER": "mistral", "MISTRAL_API_KEY": "test-secret"},
            clear=True,
        ), mock.patch("urllib.request.urlopen") as urlopen:
            provider, _ = provider_from_env()
            self.assertEqual(provider.name, "mistral")
            self.assertTrue(provider.available()[0])
            result = provider.execute(make_brief())
        self.assertEqual(result.status, "pending_human")
        self.assertFalse(result.executed)
        urlopen.assert_not_called()

    def test_paid_opt_in_sends_real_chat_completion_request(self) -> None:
        import io
        import json

        payload = {
            "id": "req-paid-test",
            "model": "mistral-small-latest",
            "choices": [{
                "message": {"content": json.dumps({
                    "summary": "Mistral answered",
                    "evidence": ["response generated"],
                    "met_criteria": ["tests_run"],
                    "artifacts": [],
                    "claims": {},
                })}
            }],
        }
        response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        with mock.patch.dict(
            os.environ,
            {
                "OMNI_PROVIDER": "mistral",
                "MISTRAL_API_KEY": "test-secret",
                "OMNI_MISTRAL_ALLOW_PAID": "1",
            },
            clear=True,
        ), mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            provider, _ = provider_from_env()
            result = provider.execute(make_brief())

        self.assertTrue(result.executed)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.summary, "Mistral answered")
        self.assertEqual(result.met_criteria, [])
        self.assertEqual(result.artifacts, [])
        self.assertEqual(result.claims["verification"], "unverified_model_output")
        self.assertEqual(result.claims["model_reported_criteria"], ["tests_run"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.mistral.ai/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["model"], "mistral-small-latest")
        self.assertEqual(sent["messages"][1]["content"], make_brief().to_text())
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertNotIn("test-secret", str(vars(result)))

    @unittest.skipIf(os.name == "nt", "POSIX file permissions are not available")
    def test_private_key_file_is_accepted_and_insecure_key_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "mistral.key"
            key_file.write_text("file-secret\n", encoding="utf-8")
            key_file.chmod(0o600)
            with mock.patch.dict(
                os.environ,
                {"OMNI_PROVIDER": "mistral", "MISTRAL_API_KEY_FILE": str(key_file)},
                clear=True,
            ):
                provider, _ = provider_from_env()
                self.assertTrue(provider.available()[0])

            key_file.chmod(0o644)
            with mock.patch.dict(
                os.environ,
                {"OMNI_PROVIDER": "mistral", "MISTRAL_API_KEY_FILE": str(key_file)},
                clear=True,
            ):
                provider, _ = provider_from_env()
                self.assertFalse(provider.available()[0])


    def test_cli_verify_is_local_only(self) -> None:
        import contextlib
        import io
        from omni.cli import main

        output = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": "test-secret"},
            clear=True,
        ), mock.patch("urllib.request.urlopen") as urlopen, contextlib.redirect_stdout(output):
            code = main(["providers", "--verify", "mistral"])
        self.assertEqual(code, 0)
        self.assertIn("network request: not sent", output.getvalue())
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
