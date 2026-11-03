"""Gestion des secrets — détection, masquage, interdiction de versionner.

Aucun secret ne doit jamais apparaître dans un livrable, un journal ou
le registre. Les tokens viennent exclusivement de variables
d'environnement (jamais codés en dur).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

# Motifs de secrets courants (clés API, tokens, mots de passe en clair).
SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),                    # tokens GitHub
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),                  # fine-grained
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                           # clés API LLM
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(r"(?i)(password|passwd|secret)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),                             # AWS
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),                 # Slack
]

_ENV_HINT = re.compile(r"os\.environ\.get\(\s*['\"]([A-Z0-9_]+)['\"]")
ALLOWED_ENV_PATTERN = re.compile(
    r"os\.environ|os\.getenv|getenv\(")


class SecretLeak(Exception):
    """Un secret a été détecté là où il ne doit jamais apparaître."""


def scan_secrets(text: str) -> List[Dict[str, Any]]:
    """Retourne les secrets détectés dans un texte (position + motif)."""
    findings = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "pattern": pattern.pattern[:40],
                "position": match.start(),
                "sample": match.group(0)[:8] + "…",
            })
    return findings


def redact(text: str) -> str:
    """Remplace chaque secret détecté par [REDACTED]."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def assert_no_secrets(text: str, context: str = "livrable") -> None:
    """Échoue brutalement si un secret est présent — utilisé partout."""
    findings = scan_secrets(text)
    if findings:
        raise SecretLeak(f"secret détecté dans {context} : "
                         f"{[f['sample'] for f in findings]} (bloqué, "
                         f"jamais journalisé intégralement)")


def require_env(name: str) -> str:
    """Récupère un secret depuis l'environnement ou échoue proprement."""
    value = os.environ.get(name, "")
    if not value:
        raise SecretLeak(f"variable d'environnement {name} absente — "
                         f"configurer le secret hors dépôt")
    return value
