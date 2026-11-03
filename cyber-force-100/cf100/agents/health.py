"""Surveillance de santé des agents — heartbeat, dégradation, reprise.

Le moniteur ne suppose jamais qu'un agent va bien : un agent sans
battement récent est marqué dégradé, et son fallback est proposé.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from cf100.agents.base import CyberAgent
from cf100.agents.models import AgentState

DEFAULT_TIMEOUT_S = 300.0


class HealthMonitor:
    """Surveille les agents déclarés et signale les défaillances."""

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s
        self.agents: Dict[str, CyberAgent] = {}

    def watch(self, agent: CyberAgent) -> None:
        self.agents[agent.spec.id] = agent

    def check(self) -> Dict[str, Any]:
        """Vérifie tous les agents ; dégrade ceux sans heartbeat récent."""
        now = time.time()
        report: Dict[str, Any] = {"healthy": [], "degraded": [], "stopped": [],
                                  "fallbacks": {}}
        for agent_id, agent in self.agents.items():
            if agent.state in (AgentState.STOPPED,):
                report["stopped"].append(agent_id)
                continue
            if agent.last_heartbeat > 0 and \
                    now - agent.last_heartbeat > self.timeout_s:
                agent.state = AgentState.DEGRADED
                report["degraded"].append(agent_id)
                if agent.spec.fallback:
                    report["fallbacks"][agent_id] = agent.spec.fallback
            else:
                report["healthy"].append(agent_id)
        return report

    def restart(self, agent_id: str) -> bool:
        """Réactive un agent dégradé (retour à l'état actif, heartbeat neuf)."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return False
        if agent.state == AgentState.DEGRADED:
            agent.state = AgentState.ACTIVE
            agent.heartbeat()
            return True
        return False

    def summary(self) -> Dict[str, int]:
        rep = self.check()
        return {
            "healthy": len(rep["healthy"]),
            "degraded": len(rep["degraded"]),
            "stopped": len(rep["stopped"]),
        }
