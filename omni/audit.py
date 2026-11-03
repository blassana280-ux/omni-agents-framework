"""Reproducible audit of the GitHub account.

``analyse_inventory`` is pure (offline-testable); ``audit_account`` performs the
real API calls with the GitHub CLI. The audit is what proved that
``blassana280-ux/optimiser-mes-agents-IA`` is not reachable and that the same
1682-byte ``AGENTS.md`` was pushed onto 38 repositories.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

INJECTED_SIZE = 1682
INJECTED_SHA = "3116c8cadc"


def _gh_json(args: List[str]) -> Any:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout or "null")


@dataclass
class RepoReport:
    name: str
    branch: str
    agents_md: str  # "injected" | "absent" | "custom"
    upstream_agents_md: str  # "exists" | "absent" | "unknown"
    overwritten: bool
    parent: str = "-"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_agents_md(size: Optional[int], sha_prefix: Optional[str]) -> str:
    if size is None:
        return "absent"
    if size == INJECTED_SIZE and (sha_prefix or "").startswith(INJECTED_SHA):
        return "injected"
    return "custom"


def analyse_inventory(rows: List[Dict[str, Any]]) -> List[RepoReport]:
    """Pure analysis over collected rows.

    Each row: ``name``, ``branch``, ``agents_md_size``, ``agents_md_sha``,
    ``upstream_agents_md_size``, ``parent``.
    """
    reports: List[RepoReport] = []
    for row in rows:
        local = classify_agents_md(row.get("agents_md_size"), row.get("agents_md_sha"))
        upstream_size = row.get("upstream_agents_md_size")
        upstream = "unknown" if row.get("parent") in (None, "-") else (
            "exists" if upstream_size else "absent"
        )
        overwritten = local == "injected" and upstream == "exists"
        notes: List[str] = []
        if overwritten:
            notes.append("upstream AGENTS.md replaced by the injected OmniBrain routing file")
        if local == "injected" and upstream == "absent":
            notes.append("OmniBrain routing file added where upstream had none (no instruction lost)")
        if local == "absent" and upstream == "exists":
            notes.append("upstream AGENTS.md not present locally")
        reports.append(
            RepoReport(
                name=row["name"],
                branch=row.get("branch", "-"),
                agents_md=local,
                upstream_agents_md=upstream,
                overwritten=overwritten,
                parent=row.get("parent") or "-",
                notes=notes,
            )
        )
    return reports


def audit_account(account: str, limit: int = 200) -> Dict[str, Any]:
    """Live audit. Requires an authenticated ``gh`` CLI."""
    repos = _gh_json([
        "repo", "list", account, "--limit", str(limit), "--json",
        "name,isFork,parent,defaultBranchRef,diskUsage,primaryLanguage,pushedAt",
    ])
    rows: List[Dict[str, Any]] = []
    for repo in repos:
        name = repo["name"]
        branch = (repo.get("defaultBranchRef") or {}).get("name", "-")
        parent = (repo.get("parent") or {}).get("nameWithOwner", "-")
        proc = subprocess.run(
            ["gh", "api", f"repos/{account}/{name}/contents/AGENTS.md?ref={branch}"],
            capture_output=True,
            text=True,
        )
        size = sha = None
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                size = data.get("size")
                sha = (data.get("sha") or "")[:10]
            except json.JSONDecodeError:
                pass
        up_size = None
        if parent != "-":
            up = subprocess.run(
                ["gh", "api", f"repos/{parent}/contents/AGENTS.md"],
                capture_output=True,
                text=True,
            )
            if up.returncode == 0:
                try:
                    up_size = json.loads(up.stdout).get("size")
                except json.JSONDecodeError:
                    up_size = None
        rows.append(
            {
                "name": name,
                "branch": branch,
                "parent": parent,
                "agents_md_size": size,
                "agents_md_sha": sha,
                "upstream_agents_md_size": up_size,
            }
        )

    reports = analyse_inventory(rows)
    return {
        "account": account,
        "repos_scanned": len(reports),
        "injected": sum(1 for r in reports if r.agents_md == "injected"),
        "overwritten": [r.name for r in reports if r.overwritten],
        "added_without_loss": [r.name for r in reports if r.agents_md == "injected" and r.upstream_agents_md == "absent"],
        "reports": [r.to_dict() for r in reports],
    }
