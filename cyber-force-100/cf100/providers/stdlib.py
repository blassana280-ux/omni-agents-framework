"""Providers d'exécution stdlib — du travail RÉEL, jamais simulé.

Chaque provider d'outil effectue une opération réelle avec la seule
bibliothèque standard : lecture de fichier avec empreinte SHA-256,
analyse statique (secrets + motifs suspects), analyse de dépendances,
analyse de journaux, vérification de la chaîne de preuves.

`make_provider_for()` construit le callable injecté dans les CyberAgent :
toute action sans implémentation réelle lève `ProviderUnavailable` —
le principe « jamais de résultat inventé » est appliqué au niveau
même de l'exécution.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List

from cf100.security.input_guard import assess
from cf100.security.secrets import scan_secrets


class ProviderUnavailable(Exception):
    """Aucune implémentation réelle pour cette action — refus de simuler."""


def _read_text(task: Dict[str, Any]) -> str:
    """Lit le fichier visé par la tâche (champ `path` obligatoire)."""
    path = task.get("path")
    if not path:
        raise ProviderUnavailable("tâche sans champ 'path' : rien à lire")
    p = Path(path)
    if not p.is_file():
        raise ProviderUnavailable(f"fichier introuvable : {path}")
    return p.read_text(encoding="utf-8", errors="replace")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- outils réels ------------------------------------------------------

def read_file(task: Dict[str, Any]) -> Dict[str, Any]:
    """Lit un fichier et retourne contenu + empreinte + métadonnées."""
    text = _read_text(task)
    return {
        "path": task["path"],
        "sha256": _sha256(text),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "size_bytes": len(text.encode("utf-8")),
        "content": text,
    }


SUSPICIOUS_PATTERN = re.compile(
    r"(?i)(eval\s*\(|exec\s*\(|os\.system|subprocess|base64\s+-d|"
    r"chmod\s+777|shell\s*=\s*True|pickle\.loads|yaml\.load\(\s*[^,)]+\))")


def analyze_file(task: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse statique réelle : secrets, injections, motifs suspects."""
    text = _read_text(task)
    secrets = scan_secrets(text)
    injection = assess(text)
    suspicious = sorted({m.group(0).strip() for m in
                         SUSPICIOUS_PATTERN.finditer(text)})
    return {
        "path": task["path"],
        "sha256": _sha256(text),
        "lines": len(text.splitlines()),
        "secrets_found": len(secrets),
        "secret_patterns": sorted({s["pattern"] for s in secrets}),
        "injection_score": injection.score,
        "suspicious_patterns": suspicious[:20],
        "verdict": ("suspect" if secrets or suspicious
                    or injection.score > 0 else "clean"),
    }


def scan_text(task: Dict[str, Any]) -> Dict[str, Any]:
    """Détection de secrets (outil scan_secrets) — échantillons tronqués,
    jamais le secret complet dans un résultat."""
    text = task.get("text") if "text" in task else _read_text(task)
    findings = scan_secrets(text)
    return {
        "count": len(findings),
        "findings": [{"pattern": f["pattern"], "position": f["position"],
                      "sample": f["sample"]} for f in findings],
        "secret_material_logged": False,
    }


def scan_dependencies(task: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse réelle d'un fichier de dépendances (style requirements).

    Détecte : versions non épinglées, doublons, sources externes
    (git+/http(s)://) — base d'un audit de chaîne d'approvisionnement.
    """
    text = _read_text(task)
    deps: List[Dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        pinned = "==" in line
        external = line.startswith(("git+", "http://", "https://")) \
            or " @ " in line and (
                "git+" in line or "http" in line)
        name = re.split(r"[=<>~\[ ]", line)[0].lower()
        deps.append({"name": name, "line": line, "pinned": pinned,
                     "external_source": external})
    names = [d["name"] for d in deps]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    return {
        "count": len(deps),
        "unpinned": [d["line"] for d in deps if not d["pinned"]],
        "duplicates": duplicates,
        "external_sources": [d["line"] for d in deps if d["external_source"]],
        "dependencies": deps,
    }


def analyze_logs(task: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse réelle de journaux : erreurs, échecs d'authentification,
    top IP sources."""
    text = _read_text(task)
    lines = text.splitlines()
    errors = sum(1 for l in lines if "ERROR" in l.upper()
                 or " CRITICAL " in l.upper())
    failed_logins = sum(
        1 for l in lines
        if re.search(r"(?i)failed\s+(login|auth|password|sign-?in)", l)
        or re.search(r"(?i)authentication\s+fail", l))
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    top_ips = Counter(ips).most_common(5)
    return {
        "lines": len(lines),
        "errors": errors,
        "failed_logins": failed_logins,
        "top_ips": [{"ip": ip, "count": n} for ip, n in top_ips],
        "verdict": ("suspect" if failed_logins > 0 or errors > 10
                    else "clean"),
    }


def verify_evidence(task: Dict[str, Any]) -> Dict[str, Any]:
    """Vérification réelle d'une chaîne de preuves."""
    from cf100.core.evidence import EvidenceEngine
    log = task.get("evidence_log")
    engine = EvidenceEngine(Path(log)) if log else EvidenceEngine()
    verdict = engine.verify()
    return verdict


# -- carte outil -> implémentation réelle --------------------------------

PROVIDER_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "read_file": read_file,
    "run_static_analysis": analyze_file,
    "run_analysis": analyze_file,
    "scan_dependencies": scan_dependencies,
    "scan_secrets": scan_text,
    "query_logs": analyze_logs,
    "verify_evidence": verify_evidence,
}


def make_provider_for(tools=None):
    """Construit un provider n'exécutant que des actions réelles.

    Une action sans implémentation réelle lève ProviderUnavailable :
    aucun agent ne « fait semblant » de travailler.
    """
    def provider(task: Dict[str, Any]) -> Dict[str, Any]:
        action = task.get("action", "execute_task")
        fn = PROVIDER_MAP.get(action)
        if fn is None:
            raise ProviderUnavailable(
                f"aucune implémentation réelle pour l'action {action} — "
                f"exécution refusée (jamais simulée)")
        return fn(task)
    return provider
