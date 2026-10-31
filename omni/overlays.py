"""Repair and refresh the ``AGENTS.md`` overlays across the account.

Two documented problems are fixed here:

* **overwritten** — an upstream ``AGENTS.md`` was replaced by the injected
  routing file. The original instructions are fetched back and the OmniBrain
  rules are appended as a separate, clearly marked section.
* **stale overlay** — a repository got the routing file glued on top of nothing,
  and that file points at the unverifiable ``optimiser-mes-agents-IA``
  reference. It is regenerated to point at this framework instead.

``plan()`` is read-only. ``apply()`` needs write access on the target repository
and refuses to invent it: a 403 is reported as ``blocked``, never as success.
"""

from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit import INJECTED_SIZE, INJECTED_SHA, _gh_json

OVERLAY_MARKER = "<!-- omnibrain-overlay:v2 -->"
FRAMEWORK = "blassana280-ux/omni-agents-framework"
BROKEN_REF = "blassana280-ux/optimiser-mes-agents-IA"

OVERLAY_TEMPLATE = """{marker}

---

<!--
  Section locale du réseau blassana280-ux — ajoutée par OmniBrain.
  Les instructions upstream ci-dessus restent la seule autorité pour ce dépôt :
  cette section ajoute des règles de travail locales, elle n'en remplace aucune.
  Supprimez ce bloc avant toute contribution upstream si le dépôt ne l'accepte pas.
-->

# Couche locale — réseau OmniBrain

## Source de vérité de l'orchestrateur

> **{framework}** → `OMNIBRAIN.md`, `registry/`, `omni/orchestrator.py`, `tests/`

La référence historique `{broken}` **n'a pas pu être vérifiée** (l'API GitHub
répond `403`, aucun accès en lecture) : elle ne doit plus être citée comme
existante.

## Règles de travail

1. **Classer avant d'agir** — simple → 1 agent ; moyenne → 1 à 3 ; complexe →
   escouade, dispatch dans une seule vague parallèle.
2. **Preuve fraîche obligatoire** — aucune affirmation sans sortie de commande,
   ligne de fichier ou réponse d'API. Verdict par défaut : « NEEDS WORK ».
3. **Réutiliser avant de créer** — chercher dans `registry/skills.json`
   (`python3 -m omni skills <termes>`) avant d'inventer un agent.
4. **Aucun secret dans le dépôt** — providers et tokens par variables
   d'environnement uniquement.
5. **Jamais d'écriture directe sur `main`** — branche + Pull Request.
6. **Respect de l'upstream** — `CONTRIBUTING.md` du dépôt prévaut, y compris
   pour la déclaration d'assistance IA.
"""


@dataclass
class OverlayAction:
    repo: str
    parent: str
    branch: str
    kind: str  # "restore+overlay" | "refresh" | "skip"
    reason: str
    new_content: str = ""
    status: str = "planned"  # planned | applied | blocked | failed
    detail: str = ""
    pr_url: str = ""
    branch_name: str = ""

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        if not include_content:
            d.pop("new_content", None)
        return d


def build_overlay() -> str:
    return OVERLAY_TEMPLATE.format(marker=OVERLAY_MARKER, framework=FRAMEWORK, broken=BROKEN_REF)


def compose_agents_md(upstream_text: str) -> str:
    """Upstream instructions first, byte-for-byte, then the separated overlay.

    Idempotent: an existing overlay section is replaced, never stacked.
    """
    marker_at = upstream_text.find(OVERLAY_MARKER)
    base = (upstream_text[:marker_at] if marker_at != -1 else upstream_text).rstrip()
    return base + "\n\n" + build_overlay()


def write_manifest(actions: List[OverlayAction], path: str | Path, handled: Optional[Dict[str, str]] = None) -> Path:
    """Write a reviewable, content-free plan (repo, kind, size, sha256).

    Lets a human verify the repair before it is applied, and check afterwards
    that the file that landed is byte-identical to the planned one.
    """
    import hashlib

    handled = handled or {}
    pending = [a for a in actions if a.kind != "skip"]
    lines = [
        "# Plan de réparation des `AGENTS.md`",
        "",
        "Généré en lecture seule par `python3 -m omni overlays --manifest <fichier>`.",
        "Aucun contenu upstream n'est inclus ici : uniquement des empreintes,",
        "pour que le résultat puisse être vérifié après application.",
        "",
        f"- dépôts scannés : **{len(actions)}**",
        f"- actions en attente : **{len(pending)}**",
        "",
        "| Dépôt | Action | Taille (octets) | sha256 |",
        "|---|---|---|---|",
    ]
    for action in pending:
        digest = hashlib.sha256(action.new_content.encode("utf-8")).hexdigest()
        kind = action.kind
        if action.repo in handled:
            kind += f" *(traité : {handled[action.repo]})*"
        lines.append(
            f"| `{action.repo}` | {kind} | {len(action.new_content.encode('utf-8'))} | `{digest[:16]}…` |"
        )
    lines += [
        "",
        "## Application",
        "",
        "```bash",
        "python3 -m omni overlays --account blassana280-ux --apply",
        "```",
        "",
        "Chaque dépôt reçoit une branche `omnibrain/agents-md-<ts>` et une Pull Request ;",
        "`main` n'est jamais écrit directement. Un refus d'écriture est rapporté comme",
        "`blocked`, jamais comme un succès.",
    ]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _decode_content(payload: Dict[str, Any]) -> str:
    return base64.b64decode(payload.get("content", "")).decode("utf-8", errors="replace")


def _get_contents(repo: str, path: str) -> Optional[Dict[str, Any]]:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def plan(account: str, limit: int = 200, only: Optional[List[str]] = None) -> List[OverlayAction]:
    """Read-only: compute the exact repair for every repository."""
    repos = _gh_json(["repo", "list", account, "--limit", str(limit), "--json", "name"])
    actions: List[OverlayAction] = []
    overlay = build_overlay()

    for repo in repos:
        name = repo["name"]
        if only and name not in only:
            continue
        # GraphQL omits `parent` in `repo list`; only the REST payload is reliable.
        meta = _gh_json(["api", f"repos/{account}/{name}"])
        branch = meta.get("default_branch", "main")
        parent = ((meta.get("parent") or {}).get("full_name") or "")
        local = _get_contents(f"{account}/{name}", "AGENTS.md")

        if local and local.get("size") == INJECTED_SIZE and str(local.get("sha", "")).startswith(INJECTED_SHA):
            local_state = "injected"
        elif local is None:
            local_state = "absent"
        else:
            local_state = "custom"

        upstream = _get_contents(parent, "AGENTS.md") if parent else None

        if local_state == "injected" and upstream is not None:
            restored = compose_agents_md(_decode_content(upstream))
            actions.append(OverlayAction(
                repo=f"{account}/{name}", parent=parent, branch=branch,
                kind="restore+overlay",
                reason=f"upstream AGENTS.md ({upstream.get('size')} bytes) was overwritten; restore it and append the local section",
                new_content=restored,
            ))
        elif local_state == "injected":
            actions.append(OverlayAction(
                repo=f"{account}/{name}", parent=parent or "-", branch=branch,
                kind="refresh",
                reason="injected overlay still points at the unverifiable reference; regenerate it",
                new_content=overlay,
            ))
        else:
            actions.append(OverlayAction(
                repo=f"{account}/{name}", parent=parent or "-", branch=branch,
                kind="skip",
                reason=f"nothing to repair (AGENTS.md {local_state})",
            ))
    return actions


def apply(action: OverlayAction, pr_body: str = "", sleep: float = 0.0) -> OverlayAction:
    """Create a branch + commit (+PR) with the corrected AGENTS.md.

    Returns ``status="blocked"`` when the token lacks write access — the honest
    outcome, never a fabricated success.
    """
    if action.kind == "skip":
        action.status = "skipped"
        return action

    slug = action.repo
    branch_name = f"omnibrain/agents-md-{int(__import__('time').time())}"
    action.branch_name = branch_name

    try:
        ref = _gh_json(["api", f"repos/{slug}/git/ref/heads/{action.branch}"])
        base_commit = ref["object"]["sha"]
        commit = _gh_json(["api", f"repos/{slug}/git/commits/{base_commit}"])
        base_tree = commit["tree"]["sha"]

        blob = _post(slug, "git/blobs", {"content": action.new_content, "encoding": "utf-8"})
        if blob is None:
            return _blocked(action, "cannot create blob (write access missing)")
        tree = _post(slug, "git/trees", {
            "base_tree": base_tree,
            "tree": [{"path": "AGENTS.md", "mode": "100644", "type": "blob", "sha": blob["sha"]}],
        })
        if tree is None:
            return _blocked(action, "cannot create tree (write access missing)")
        message = (
            "docs(agents): restore upstream AGENTS.md and isolate the OmniBrain section\n\n"
            + action.reason
            + f"\n\nOmniBrain source of truth: {FRAMEWORK}/OMNIBRAIN.md\n"
            + f"Unverifiable reference removed: {BROKEN_REF}\n"
        )
        new_commit = _post(slug, "git/commits", {
            "message": message, "tree": tree["sha"], "parents": [base_commit],
        })
        if new_commit is None:
            return _blocked(action, "cannot create commit (write access missing)")
        created = _post(slug, "git/refs", {"ref": f"refs/heads/{branch_name}", "sha": new_commit["sha"]})
        if created is None:
            return _blocked(action, "cannot create branch (write access missing)")
        action.status = "applied"
        action.detail = f"commit {new_commit['sha'][:10]} on {branch_name}"

        if pr_body:
            proc = subprocess.run(
                ["gh", "pr", "create", "--repo", slug, "--base", action.branch,
                 "--head", branch_name,
                 "--title", "docs(agents): restore upstream AGENTS.md + isolate OmniBrain section",
                 "--body", pr_body],
                capture_output=True, text=True,
            )
            if proc.returncode == 0:
                action.pr_url = proc.stdout.strip().splitlines()[-1]
            else:
                action.detail += f"; PR failed: {proc.stderr.strip()[:200]}"
        return action
    except (RuntimeError, KeyError, TypeError) as exc:
        action.status = "failed"
        action.detail = str(exc)[:300]
        return action


def _post(slug: str, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    proc = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{slug}/{path}", "--input", "-"],
        input=json.dumps(payload), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _blocked(action: OverlayAction, detail: str) -> OverlayAction:
    action.status = "blocked"
    action.detail = detail
    return action
