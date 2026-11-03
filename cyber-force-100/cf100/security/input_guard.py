"""Garde anti-injection de prompts et instructions malveillantes.

Toute donnée externe (résultat d'agent, contenu de dépôt, flux CTI) passe
par assess() avant d'atteindre une décision ou une exécution. Un texte
suspect est signalé, neutralisé et journalisé — jamais exécuté.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)ignore\s+(all\s+|any\s+|the\s+)?"
               r"(previous\s+|prior\s+|above\s+)?"
               r"(instructions|prompts?|rules)"),
    re.compile(r"(?i)disregard (all|your|the) (previous|prior) (instructions|rules)"),
    re.compile(r"(?i)you are now (a|an|the)"),
    re.compile(r"(?i)new instructions:?"),
    re.compile(r"(?i)system prompt\s*:", re.IGNORECASE),
    re.compile(r"(?i)reveal (your|the) (system|initial) (prompt|instructions)"),
    re.compile(r"(?i)reveal\s+(your\s+|the\s+|all\s+)?"
               r"(secrets?|tokens?|credentials?|keys?|env(ironment)?\s*"
               r"(vars?|variables?))"),
    re.compile(r"(?i)exfiltrat(e|ion)"),
    re.compile(r"(?i)send (all|the) (secrets?|tokens?|credentials?|data) (to|at)"),
    re.compile(r"(?i)curl\s+\S+\s*\|\s*(ba)?sh"),        # pipe to shell
    re.compile(r"(?i)base64\s+-d\s*\|\s*(ba)?sh"),
    re.compile(r"(?i)eval\(atob\("),
    re.compile(r"(?i)<script>"),
    re.compile(r"(?i)onerror\s*="),
    re.compile(r"(?i)chmod\s+777"),
]

SAFE_MARKER = "[INJECTION-NEUTRALIZED]"


@dataclass
class InjectionReport:
    """Résultat de l'évaluation d'un texte entrant."""

    safe: bool
    score: int
    matches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"safe": self.safe, "score": self.score,
                "matches": self.matches}


def assess(text: str) -> InjectionReport:
    """Évalue un texte : score = nombre de motifs d'injection détectés."""
    matches = [p.pattern[:48] for p in INJECTION_PATTERNS if p.search(text)]
    return InjectionReport(safe=not matches, score=len(matches),
                           matches=matches)


def neutralize(text: str) -> str:
    """Neutralise les motifs d'injection détectés dans un texte."""
    for p in INJECTION_PATTERNS:
        text = p.sub(SAFE_MARKER, text)
    return text


def gate_external(content: str, source: str,
                  logger=None) -> InjectionReport:
    """Point de passage obligatoire des données externes.

    Le contenu est évalué puis neutralisé ; le verdict est journalisé
    via le logger fourni (EvidenceEngine) avec la source d'origine.
    """
    report = assess(content)
    if not report.safe and logger is not None:
        logger.record("injection_blocked", source=source,
                      score=report.score)
    return report
