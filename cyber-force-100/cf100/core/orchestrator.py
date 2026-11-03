"""Agent Orchestrator — répartition intelligente des tâches.

Sélectionne les agents par compétences, respecte les fallbacks, exécute
en parallèle réel (ThreadPoolExecutor comme OmniBrain) et enregistre
chaque dispatch dans les preuves. Il n'exécute jamais une action refusée
par le moteur de politiques.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from cf100.agents.base import ActionDenied, CyberAgent
from cf100.agents.models import AgentSpec
from cf100.core.evidence import EvidenceEngine


class NoAgentFound(Exception):
    """Aucun agent ne couvre la compétence demandée — jamais simulé."""


class Orchestrator:
    """Répartit les tâches vers les agents par compétence."""

    def __init__(self, agents: Dict[str, CyberAgent],
                 evidence: EvidenceEngine, max_workers: int = 4):
        self.agents = agents
        self.evidence = evidence
        self.max_workers = max_workers

    # -- sélection ------------------------------------------------------
    def select(self, skill: str, count: int = 1) -> List[CyberAgent]:
        """Sélectionne jusqu'à `count` agents couvrant la compétence."""
        candidates = [a for a in self.agents.values()
                      if skill in a.spec.skills]
        if not candidates:
            raise NoAgentFound(
                f"aucun agent avec la compétence {skill} — création d'un "
                f"agent dynamique possible via cf100.agents.dynamic")
        candidates.sort(key=lambda a: (a.tasks_failed, -a.tasks_done))
        return candidates[:count]

    # -- exécution --------------------------------------------------------
    def run_task(self, skill: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assigne et exécute une tâche chez l'agent le plus disponible."""
        agents = self.select(skill)
        agent = agents[0]
        self.evidence.record("dispatch", agent=agent.spec.id,
                             skill=skill, action=task.get("action"))
        try:
            result = agent.execute(task)
            return {"agent": agent.spec.id, "ok": True, "result": result}
        except ActionDenied as exc:
            fallback_id = agent.spec.fallback
            if fallback_id and fallback_id in self.agents:
                fb = self.agents[fallback_id]
                self.evidence.record("fallback_used", agent=fb.spec.id,
                                     reason=str(exc))
                result = fb.execute(task)
                return {"agent": fb.spec.id, "ok": True, "result": result,
                        "fallback_for": agent.spec.id}
            return {"agent": agent.spec.id, "ok": False, "error": str(exc)}

    def run_wave(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exécute en parallèle réel les tâches sans dépendance mutuelle."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(self.run_task, t["skill"], t["task"])
                       for t in tasks]
            return [f.result() for f in futures]
