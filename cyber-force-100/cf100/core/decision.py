"""Adaptive Decision Engine — décisions déterministes, apprentissage encadré.

Les décisions sont des règles explicites pondérées (reproductibles et
auditables, jamais inventées par un modèle). L'apprentissage ajuste les
pondérations uniquement après un retour validé, et chaque ajustement
est historisé dans la mémoire des décisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Règles par défaut : (nom, condition(risque, contexte), poids)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "risk_high": -2.0,
    "risk_critical": -5.0,
    "agent_healthy": +1.5,
    "agent_degraded": -2.0,
    "approved_action": +3.0,
    "injection_flagged": -4.0,
    "fallback_available": +0.5,
}
THRESHOLD_EXECUTE = 0.0


@dataclass
class ActionPlan:
    """Plan produit par le moteur décisionnel."""

    action: str
    execute: bool
    score: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "execute": self.execute,
                "score": self.score, "reasons": self.reasons}


class DecisionEngine:
    """Évalue une situation et décide d'exécuter ou de planifier."""

    def __init__(self, weights: Optional[Dict[str, float]] = None,
                 memory=None):
        self.weights: Dict[str, float] = dict(
            weights if weights is not None else DEFAULT_WEIGHTS)
        self.memory = memory  # MemoryTiers optionnel pour persister

    # -- décision -----------------------------------------------------
    def decide(self, action: str, risk: str,
               context: Optional[Dict[str, Any]] = None) -> ActionPlan:
        context = context or {}
        score = 0.0
        reasons: List[str] = []
        if risk == "high":
            score += self.weights["risk_high"]
            reasons.append("risque élevé")
        elif risk == "critical":
            score += self.weights["risk_critical"]
            reasons.append("risque critique")
        health = context.get("agent_health", "healthy")
        if health == "healthy":
            score += self.weights["agent_healthy"]
            reasons.append("agent sain")
        elif health in ("degraded", "stopped"):
            score += self.weights["agent_degraded"]
            reasons.append(f"agent {health}")
        if context.get("human_approved"):
            score += self.weights["approved_action"]
            reasons.append("validation humaine présente")
        if context.get("injection_score", 0) > 0:
            score += self.weights["injection_flagged"]
            reasons.append("injection détectée dans les entrées")
        if context.get("fallback"):
            score += self.weights["fallback_available"]
            reasons.append("fallback disponible")
        plan = ActionPlan(action=action, execute=score > THRESHOLD_EXECUTE,
                          score=round(score, 3), reasons=reasons)
        if self.memory is not None:
            self.memory.log_decision(
                actor="decision-engine", kind="auto",
                action=action, risk=risk,
                payload={"score": plan.score, "execute": plan.execute,
                         "reasons": reasons})
        return plan

    # -- apprentissage encadré ----------------------------------------
    def learn(self, outcome: Dict[str, Any]) -> Dict[str, float]:
        """Ajuste les poids d'après un retour d'expérience VALIDÉ.

        Le retour doit porter {"validated": True, "signals": [...]} :
        un retour non validé ne modifie jamais le comportement
        (règle d'apprentissage contrôlé).
        """
        if not outcome.get("validated"):
            return dict(self.weights)
        delta = float(outcome.get("delta", 0.1))
        for signal, direction in outcome.get("signals", []):
            if signal in self.weights:
                self.weights[signal] = round(
                    self.weights[signal] + delta * float(direction), 3)
        if self.memory is not None:
            self.memory.log_decision(
                actor="decision-engine", kind="learning",
                action="weights_update", risk="medium",
                payload={"weights": dict(self.weights)})
        return dict(self.weights)

    def snapshot_weights(self) -> str:
        return json.dumps(self.weights, indent=2)
