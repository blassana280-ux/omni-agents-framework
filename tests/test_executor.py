"""Real subprocess execution and truthful provider detection.

These tests spawn actual processes; nothing here is simulated.
"""

from __future__ import annotations

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
from omni.models import Brief


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

    def test_brief_file_is_written_and_prompt_substituted(self) -> None:
        provider = SubprocessProvider(
            command=[sys.executable, "-c", "import sys;print(len(sys.argv[1])>100)", "{prompt}"]
        )
        result = provider.execute(make_brief(), self.workdir)
        self.assertEqual(result.summary.strip(), "True")
        self.assertTrue((self.workdir / ".omni-brief-t1-test.md").is_file())


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


if __name__ == "__main__":
    unittest.main()
