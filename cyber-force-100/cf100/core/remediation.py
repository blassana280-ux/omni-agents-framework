"""Autonomous Remediation Engine — correction contrôlée.

Chaque étape d'un runbook est soumise au moteur de politiques AVANT
exécution. Une étape dangereuse produit un ticket d'approbation humaine
et n'est JAMAIS exécutée sans validation. Les étapes refusées sont
journalisées dans les preuves avec leur motif.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cf100.agents.models import AgentSpec
from cf100.core.evidence import EvidenceEngine
from cf100.security.policy import PolicyEngine


class RemediationBlocked(Exception):
    """Étape refusée par les politiques — validation humaine requise."""


@dataclass
class RemediationStep:
    """Une étape de runbook de remédiation."""

    name: str
    action: str
    executor: Any = None          # callable() -> résultat, injecté
    params: Optional[Dict[str, Any]] = None


class RemediationEngine:
    """Exécute des runbooks de remédiation, étape par étape, encadré."""

    def __init__(self, policy: PolicyEngine, evidence: EvidenceEngine):
        self.policy = policy
        self.evidence = evidence

    def run_playbook(self, agent: AgentSpec, playbook: str,
                     steps: List[RemediationStep]) -> Dict[str, Any]:
        """Exécute un runbook ; s'arrête à la première étape bloquée."""
        results: List[Dict[str, Any]] = []
        for step in steps:
            decision = self.policy.authorize(agent, step.action,
                                             {"playbook": playbook})
            if not decision.allowed or decision.needs_approval:
                self.evidence.record(
                    "remediation_blocked", agent=agent.id,
                    playbook=playbook, step=step.name,
                    action=step.action, reason=decision.reason)
                results.append({"step": step.name, "status": "blocked",
                                 "reason": decision.reason})
                return {"playbook": playbook, "status": "blocked",
                        "results": results,
                        "needs_human_approval": step.action}
            if step.executor is None:
                results.append({"step": step.name, "status": "no_executor"})
                continue
            outcome = step.executor()
            self.evidence.record("remediation_step", agent=agent.id,
                                  playbook=playbook, step=step.name,
                                  action=step.action)
            results.append({"step": step.name, "status": "done",
                            "result": outcome})
        self.evidence.record("remediation_done", agent=agent.id,
                              playbook=playbook)
        return {"playbook": playbook, "status": "done", "results": results}
