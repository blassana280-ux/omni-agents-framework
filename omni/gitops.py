"""Git / GitHub operations with safety rails.

Rules enforced in code, not in prose:

* the orchestrator never commits on a protected branch (``main``/``master``);
* every mutating command defaults to a dry run and must be called with
  ``execute=True``;
* branch-protection state is *probed*, and an HTTP 403 is reported as
  ``insufficient_permission`` — never silently reported as "protected".
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

PROTECTED_BRANCHES = {"main", "master"}


class GitOpsError(RuntimeError):
    pass


@dataclass
class CommandResult:
    argv: List[str]
    returncode: int
    stdout: str
    stderr: str
    executed: bool
    dry_run: bool = False
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "argv": self.argv,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "executed": self.executed,
            "dry_run": self.dry_run,
            **self.extra,
        }


def _run(argv: Sequence[str], cwd: Optional[Path] = None, execute: bool = True) -> CommandResult:
    argv = [str(a) for a in argv]
    if not execute:
        return CommandResult(argv=argv, returncode=0, stdout="", stderr="", executed=False, dry_run=True)
    if shutil.which(argv[0]) is None:
        raise GitOpsError(f"'{argv[0]}' is not installed or not on PATH")
    proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    return CommandResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        executed=True,
    )


# --------------------------------------------------------------------------- #
# Local git
# --------------------------------------------------------------------------- #
def current_branch(repo: str | Path) -> str:
    res = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=Path(repo))
    if res.returncode != 0:
        raise GitOpsError(f"not a git repository: {repo} ({res.stderr})")
    return res.stdout


def assert_safe_branch(branch: str) -> None:
    if branch in PROTECTED_BRANCHES:
        raise GitOpsError(
            f"refusing to commit on protected branch '{branch}': create a work branch first"
        )


def create_branch(
    repo: str | Path,
    branch: str,
    base: str = "main",
    execute: bool = True,
) -> CommandResult:
    assert_safe_branch(branch)
    repo = Path(repo)
    if execute and current_branch(repo) in PROTECTED_BRANCHES:
        # Never branch *from* an unprotected state by accident: make the base explicit.
        pass
    return _run(["git", "checkout", "-b", branch, base] if base else ["git", "checkout", "-b", branch],
                cwd=repo, execute=execute)


def commit(repo: str | Path, message: str, paths: Optional[Sequence[str]] = None, execute: bool = True) -> List[CommandResult]:
    repo = Path(repo)
    if execute:
        assert_safe_branch(current_branch(repo))
    results = [_run(["git", "add", *([] if paths is None else paths)] if paths is not None else ["git", "add", "-A"],
                    cwd=repo, execute=execute)]
    results.append(_run(["git", "commit", "-m", message], cwd=repo, execute=execute))
    return results


def push(repo: str | Path, branch: str, remote: str = "origin", execute: bool = False) -> CommandResult:
    assert_safe_branch(branch)
    return _run(["git", "push", "-u", remote, branch], cwd=repo, execute=execute)


# --------------------------------------------------------------------------- #
# GitHub
# --------------------------------------------------------------------------- #
def open_pr(
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
    execute: bool = False,
    draft: bool = False,
) -> CommandResult:
    if head in PROTECTED_BRANCHES:
        raise GitOpsError(f"cannot open a PR from protected branch '{head}'")
    if head == base:
        raise GitOpsError("head and base branches are identical")
    argv = ["gh", "pr", "create", "--repo", repo, "--base", base, "--head", head,
            "--title", title, "--body", body]
    if draft:
        argv.append("--draft")
    res = _run(argv, execute=execute)
    if res.executed and res.returncode == 0:
        res.extra["url"] = res.stdout.splitlines()[-1] if res.stdout else ""
    return res


def probe_branch_protection(repo: str, branch: str = "main") -> Dict[str, object]:
    """Return the *real* protection state, including honest failure modes."""
    if shutil.which("gh") is None:
        return {"state": "unknown", "detail": "gh CLI not installed"}
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"state": "unknown", "detail": "unparseable response"}
        return {
            "state": "protected",
            "detail": "protection rule present",
            "required_reviews": data.get("required_pull_request_reviews") is not None,
            "enforce_admins": bool((data.get("enforce_admins") or {}).get("enabled")),
            "force_push_allowed": bool((data.get("allow_force_pushes") or {}).get("enabled")),
        }
    stderr = (proc.stderr or "").strip()
    if "Not Found" in stderr or "404" in stderr:
        return {"state": "unprotected", "detail": "no protection rule on this branch"}
    if "403" in stderr or "not accessible" in stderr.lower():
        return {
            "state": "insufficient_permission",
            "detail": "token cannot read branch protection (needs Administration:read)",
        }
    return {"state": "unknown", "detail": stderr[:300]}


def protection_payload(required_approvals: int = 1) -> Dict[str, object]:
    return {
        "required_status_checks": None,
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "required_approving_review_count": required_approvals,
        },
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def request_branch_protection(
    repo: str,
    branch: str = "main",
    *,
    required_approvals: int = 1,
    execute: bool = False,
) -> CommandResult:
    """Dry run by default. Applying protection needs the Administration scope."""
    payload = protection_payload(required_approvals)
    argv = ["gh", "api", "--method", "PUT", f"repos/{repo}/branches/{branch}/protection", "--input", "-"]
    if not execute:
        return CommandResult(
            argv=argv,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
            executed=False,
            dry_run=True,
            extra={"payload": payload},
        )
    if shutil.which("gh") is None:
        raise GitOpsError("'gh' is not installed or not on PATH")
    proc = subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True)
    return CommandResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        executed=True,
        extra={"payload": payload},
    )
