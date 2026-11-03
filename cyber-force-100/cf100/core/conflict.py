"""Conflict Resolution Engine — arbitrage explicite, jamais au hasard.

Règle ordonnée (alignée sur l'arbitrage OmniBrain) :
    nombre de preuves > exécution réelle > critères satisfaits > id agent
Égalité parfaite => conflit non résolu, escalade humaine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    """Position d'un agent sur un sujet donné."""

    agent: str
    subject: str
    claim: str
    evidence_count: int
    executed: bool
    criteria_met: int

    def rank(self) -> tuple:
        return (self.evidence_count, int(self.executed), self.criteria_met)


def resolve(findings: List[Finding]) -> Dict[str, Any]:
    """Tranche un ensemble de positions contradictoires."""
    if not findings:
        return {"resolved": False, "winner": None,
                "reason": "aucune position soumise"}
    by_subject: Dict[str, List[Finding]] = {}
    for f in findings:
        by_subject.setdefault(f.subject, []).append(f)
    winners: Dict[str, Optional[str]] = {}
    unresolved: List[str] = []
    for subject, group in by_subject.items():
        if len(group) == 1:
            winners[subject] = group[0].agent
            continue
        ordered = sorted(group, key=lambda f: f.rank(), reverse=True)
        top_rank = ordered[0].rank()
        tied = [f for f in ordered if f.rank() == top_rank]
        if len(tied) > 1:
            winners[subject] = None
            unresolved.append(subject)
        else:
            winners[subject] = tied[0].agent
    return {
        "resolved": not unresolved,
        "winners": winners,
        "unresolved": unresolved,
        "rule": "evidence_count > executed > criteria_met > agent_id",
    }
