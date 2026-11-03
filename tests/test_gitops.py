"""Scenarios 8 and 9 — branch/PR integration and protected-branch handling.

The git operations run against a real temporary repository. GitHub calls are
exercised through a fake ``gh`` executable placed on PATH (a real subprocess is
spawned, so argument construction and error handling are genuinely tested).
A live check against the real account runs only when ``OMNI_LIVE=1``.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni import gitops

GIT_ENV = {
    "GIT_AUTHOR_NAME": "OmniBrain Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "OmniBrain Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


class TestGitWorkflow(unittest.TestCase):
    """Scenario 8 — a work branch is created; main is never written to."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "OmniBrain Test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "initial commit")
        self.initial = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_creates_branch_and_commits_without_touching_main(self) -> None:
        result = gitops.create_branch(self.repo, "omni/fix-1", base="main")
        self.assertTrue(result.executed)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(gitops.current_branch(self.repo), "omni/fix-1")

        (self.repo / "feature.txt").write_text("work\n", encoding="utf-8")
        commits = gitops.commit(self.repo, "feat: add feature", paths=["feature.txt"])
        self.assertTrue(all(c.returncode == 0 for c in commits), [c.stderr for c in commits])
        self.assertNotEqual(git(self.repo, "rev-parse", "HEAD"), self.initial)
        # main still points at the original commit
        self.assertEqual(git(self.repo, "rev-parse", "main"), self.initial)
        self.assertIn("feature.txt", git(self.repo, "show", "--name-only", "--format=", "HEAD"))

    def test_refuses_to_commit_on_main(self) -> None:
        self.assertEqual(gitops.current_branch(self.repo), "main")
        with self.assertRaises(gitops.GitOpsError):
            gitops.commit(self.repo, "nope")

    def test_refuses_to_create_or_push_a_protected_branch(self) -> None:
        for branch in ("main", "master"):
            with self.assertRaises(gitops.GitOpsError):
                gitops.create_branch(self.repo, branch)
            with self.assertRaises(gitops.GitOpsError):
                gitops.push(self.repo, branch)

    def test_dry_run_executes_nothing(self) -> None:
        res = gitops.create_branch(self.repo, "omni/dry", execute=False)
        self.assertFalse(res.executed)
        self.assertTrue(res.dry_run)
        self.assertEqual(gitops.current_branch(self.repo), "main")


class TestPullRequestCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name) / "bin"
        self.bin.mkdir()
        self.log = Path(self.tmp.name) / "gh.log"
        script = self.bin / "gh"
        script.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "$*" >> "{self.log}"\n'
            'if [ "$1" = "api" ] && [[ "$*" == *"protection"* ]]; then\n'
            '  if [ -n "$GH_FAKE_PROTECTION_BODY" ]; then echo "$GH_FAKE_PROTECTION_BODY"; exit 0; fi\n'
            '  echo "gh: Resource not accessible by integration (HTTP 403)" >&2; exit 1\n'
            'fi\n'
            'echo "https://github.com/blassana280-ux/omni-agents-framework/pull/42"\n',
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        self.env = mock.patch.dict(os.environ, {"PATH": f"{self.bin}:{os.environ['PATH']}"})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_open_pr_builds_and_runs_the_github_command(self) -> None:
        res = gitops.open_pr(
            "blassana280-ux/omni-agents-framework",
            head="omni/fix-1",
            base="main",
            title="feat: omni",
            body="body",
            execute=True,
        )
        self.assertTrue(res.executed)
        self.assertEqual(res.returncode, 0)
        self.assertIn("/pull/42", str(res.extra.get("url", "")))
        logged = self.log.read_text(encoding="utf-8")
        self.assertIn("pr create", logged)
        self.assertIn("--base main", logged)
        self.assertIn("--head omni/fix-1", logged)

    def test_open_pr_dry_run_does_not_call_gh(self) -> None:
        res = gitops.open_pr("o/r", head="feat", base="main", title="t", body="b", execute=False)
        self.assertFalse(res.executed)
        self.assertFalse(self.log.exists())

    def test_open_pr_rejects_protected_head_or_identical_branch(self) -> None:
        with self.assertRaises(gitops.GitOpsError):
            gitops.open_pr("o/r", head="main", base="main", title="t", body="b")
        with self.assertRaises(gitops.GitOpsError):
            gitops.open_pr("o/r", head="feat", base="feat", title="t", body="b")


class TestBranchProtectionProbe(unittest.TestCase):
    """Scenario 9 — protection state is reported truthfully, never guessed."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name) / "bin"
        self.bin.mkdir()
        self.env = mock.patch.dict(os.environ, {"PATH": f"{self.bin}:{os.environ['PATH']}"})

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_insufficient_permission_is_not_reported_as_protected(self) -> None:
        script = self.bin / "gh"
        script.write_text(
            '#!/usr/bin/env bash\necho "gh: Resource not accessible by integration (HTTP 403)" >&2\nexit 1\n',
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        self.env.start()
        probe = gitops.probe_branch_protection("blassana280-ux/omni-agents-framework", "main")
        self.assertEqual(probe["state"], "insufficient_permission")
        self.assertIn("Administration", probe["detail"])

    def test_protected_branch_is_detected(self) -> None:
        script = self.bin / "gh"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "echo '{\"required_pull_request_reviews\":{\"required_approving_review_count\":1},"
            "\"enforce_admins\":{\"enabled\":false},\"allow_force_pushes\":{\"enabled\":false}}'\n",
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        self.env.start()
        probe = gitops.probe_branch_protection("o/r", "main")
        self.assertEqual(probe["state"], "protected")
        self.assertFalse(probe["force_push_allowed"])

    def test_missing_rule_is_unprotected(self) -> None:
        script = self.bin / "gh"
        script.write_text(
            '#!/usr/bin/env bash\necho "gh: Branch not protected (HTTP 404)" >&2\nexit 1\n',
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        self.env.start()
        probe = gitops.probe_branch_protection("o/r", "main")
        self.assertEqual(probe["state"], "unprotected")

    def test_request_protection_is_a_dry_run_by_default(self) -> None:
        res = gitops.request_branch_protection("o/r", "main")
        self.assertFalse(res.executed)
        payload = res.extra["payload"]
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])
        self.assertEqual(payload["required_pull_request_reviews"]["required_approving_review_count"], 1)


@unittest.skipUnless(os.environ.get("OMNI_LIVE") == "1", "live GitHub probe disabled (set OMNI_LIVE=1)")
class TestLiveGitHubProbe(unittest.TestCase):
    """Real API call. Records whatever the token is actually allowed to do."""

    def test_live_probe_returns_a_known_state(self) -> None:
        probe = gitops.probe_branch_protection("blassana280-ux/omni-agents-framework", "main")
        self.assertIn(probe["state"], {"protected", "unprotected", "insufficient_permission", "unknown"})
        print(f"\n[live] branch protection main: {probe}")


if __name__ == "__main__":
    unittest.main()
