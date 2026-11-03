"""Mission Supervisor — boucle d'exploitation encadrée, vague par vague.

Le superviseur enchaîne des vagues de demandes via le Command Core,
vérifie la santé des agents entre les vagues et ne permet à l'apprentissage
de modifier les poids décisionnels QUE si la chaîne de preuves du cycle
est intègre. Un journal falsifié ne peut donc jamais servir à apprendre.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cf100.agents.health import HealthMonitor
from cf100.core.command import CommandCore
from cf100.core.decision import DecisionEngine
from cf100.core.evidence import EvidenceEngine


class MissionSupervisor:
    """Pilote des cycles de mission : exécution, santé, apprentissage."""

    def __init__(self, core: CommandCore, evidence: EvidenceEngine,
                 decision: DecisionEngine,
                 health: Optional[HealthMonitor] = None):
        self.core = core
        self.evidence = evidence
        self.decision = decision
        self.health = health

    def run_cycle(self, waves: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Exécute des vagues de demandes ; santé entre vagues ;
        apprentissage conditionné à l'intégrité des preuves."""
        results: List[Dict[str, Any]] = []
        health_reports: List[Dict[str, Any]] = []
        for wave in waves:
            for item in wave:
                results.append(self.core.handle(
                    item["request"], item["skill"], item.get("task")))
            if self.health is not None:
                report = self.health.check()
                health_reports.append({
                    "degraded": report.get("degraded", []),
                    "stopped": report.get("stopped", []),
                })
        # Le cycle ne peut apprendre que sur des preuves intègres.
        chain = self.evidence.verify()
        chain_ok = bool(chain.get("ok"))
        signals: List[Any] = []
        if results and all(r.get("ok") for r in results):
            # signal positif uniquement sur un cycle entièrement réussi ;
            # un rejet d'injection attendu n'émet aucun signal négatif
            signals.append(("agent_healthy", 1.0))
        before = dict(self.decision.weights)
        self.decision.learn({"validated": chain_ok,
                             "signals": signals, "delta": 0.05})
        learned = self.decision.weights != before
        return {
            "results": results,
            "chain_ok": chain_ok,
            "chain": chain,
            "health": health_reports,
            "learning_applied": learned,
        }
