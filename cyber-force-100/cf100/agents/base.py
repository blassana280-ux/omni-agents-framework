"""Cycle de vie commun des agents Cyber Force 100.

CyberAgent est l'enveloppe d'exécution réelle d'un AgentSpec :
- transitions d'état contrôlées ;
- vérification Zero Trust avant chaque action ;
- enregistrement systématique dans le journal de preuves ;
- mémoire individuelle lisible/écrivable, mémoire collective protégée.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from cf100.agents.models import AgentSpec, AgentState, Autonomy
from cf100.core.evidence import EvidenceEngine
from cf100.memory.tiers import MemoryTiers
from cf100.security.policy import PolicyEngine
from cf100.security.zero_trust import Principal, authenticate


class ActionDenied(Exception):
    """Action refusée par le moteur de politiques ou le Zero Trust."""


class CyberAgent:
    """Enveloppe d'exécution d'un agent du registre.

    Le "provider" est une fonction callable(task) -> result injectée par
    l'orchestrateur : Cyber Force 100 n'exécute jamais du code arbitraire
    d'un agent sans fournisseur explicite, et n'affirme jamais qu'un agent
    a travaillé sans provider.
    """

    def __init__(self, spec: AgentSpec, evidence: EvidenceEngine,
                 memory: MemoryTiers, policy: PolicyEngine,
                 provider: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.spec = spec
        self.evidence = evidence
        self.memory = memory
        self.policy = policy
        self.provider = provider
        self.state = AgentState.DORMANT
        self.last_heartbeat: float = 0.0
        self.tasks_done = 0
        self.tasks_failed = 0

    # -- identité ----------------------------------------------------
    def principal(self) -> Principal:
        return authenticate(self.spec.id)

    # -- cycle de vie ------------------------------------------------
    def activate(self) -> None:
        if self.state not in (AgentState.DORMANT, AgentState.STOPPED):
            raise ActionDenied(f"{self.spec.id} : activation impossible "
                               f"depuis {self.state.value}")
        self.state = AgentState.ACTIVE
        self.heartbeat()

    def stop(self) -> None:
        self.state = AgentState.STOPPED

    def heartbeat(self) -> None:
        """Batttement de vie, exploité par le moniteur de santé."""
        self.last_heartbeat = time.time()

    # -- actions -----------------------------------------------------
    def check_action(self, action: str, context: Optional[Dict] = None) -> None:
        """Vérifie que l'agent peut faire cette action, sinon lève ActionDenied."""
        if action in self.spec.denied_actions:
            raise ActionDenied(f"{self.spec.id} : action interdite par son "
                               f"profil ({action})")
        decision = self.policy.authorize(self.spec, action, context or {})
        if not decision.allowed:
            raise ActionDenied(
                f"{self.spec.id} : action {action} refusée — {decision.reason}")
        if decision.needs_approval:
            self.state = AgentState.AWAITING_APPROVAL
            raise ActionDenied(
                f"{self.spec.id} : action {action} exige une validation "
                f"humaine avant exécution ({decision.reason})")

    def execute(self, task: Dict[str, Any]) -> Any:
        """Exécute une tâche via le provider, avec preuve et traçabilité.

        Toute action de la tâche est validée avant exécution. Un agent sans
        provider échoue explicitement — il ne simule jamais de résultat.
        """
        action = task.get("action", "execute_task")
        self.check_action(action, task.get("context"))
        if self.provider is None:
            # refus explicite : ce n'est ni un échec d'exécution ni une
            # simulation — l'agent n'a jamais prétendu travailler
            self.evidence.record("task_refused", agent=self.spec.id,
                                reason="aucun provider configuré")
            raise ActionDenied(
                f"{self.spec.id} : aucun provider — le travail ne peut pas "
                f"être exécuté (jamais simulé)")
        prev = self.state
        self.state = AgentState.EXECUTING
        self.evidence.record("task_start", agent=self.spec.id, action=action)
        try:
            result = self.provider(task)
        except Exception:
            self.tasks_failed += 1
            self.state = AgentState.DEGRADED
            self.evidence.record("task_failed", agent=self.spec.id,
                                action=action)
            raise
        self.tasks_done += 1
        self.state = prev if prev == AgentState.ACTIVE else AgentState.ACTIVE
        self.heartbeat()
        self.evidence.record("task_done", agent=self.spec.id, action=action)
        return result

    # -- mémoire -----------------------------------------------------
    def remember(self, key: str, value: Any) -> None:
        """Écrit dans la mémoire individuelle de l'agent."""
        self.memory.remember_individual(self.spec.id, key, value)

    def recall(self, key: str) -> Optional[Any]:
        return self.memory.recall_individual(self.spec.id, key)

    def status(self) -> Dict[str, Any]:
        return {
            "id": self.spec.id,
            "name": self.spec.name,
            "division": self.spec.division_code,
            "state": self.state.value,
            "autonomy": self.spec.autonomy.value,
            "risk_class": self.spec.risk_class.value,
            "tasks_done": self.tasks_done,
            "tasks_failed": self.tasks_failed,
            "last_heartbeat": self.last_heartbeat,
        }
