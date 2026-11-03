"""Command Core — centre de commandement de Cyber Force 100.

Point d'entrée unique des demandes : classification déterministe,
routage vers l'orchestrateur, enregistrement systématique dans les
preuves et coordination avec les moteurs (décision, prédiction,
remédiation, santé).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cf100.agents.base import CyberAgent
from cf100.core.decision import DecisionEngine
from cf100.core.evidence import EvidenceEngine
from cf100.core.orchestrator import NoAgentFound, Orchestrator
from cf100.core.predictive import PredictiveEngine
from cf100.memory.tiers import MemoryTiers
from cf100.security.input_guard import assess
from cf100.security.policy import PolicyEngine

COMPLEXITY_MARKERS = ("escouade", "end-to-end", "de bout en bout",
                      "fullstack", "audit complet", "incident")


class CommandCore:
    """Reçoit une demande, décide, répartit, trace."""

    def __init__(self, orchestrator: Orchestrator, policy: PolicyEngine,
                 evidence: EvidenceEngine, memory: MemoryTiers,
                 decision: Optional[DecisionEngine] = None,
                 predictive: Optional[PredictiveEngine] = None):
        self.orchestrator = orchestrator
        self.policy = policy
        self.evidence = evidence
        self.memory = memory
        self.decision = decision if decision is not None else DecisionEngine()
        self.predictive = (predictive if predictive is not None
                           else PredictiveEngine())

    # -- classification déterministe ------------------------------------
    def classify(self, request: str) -> str:
        request_l = request.lower()
        if any(m in request_l for m in COMPLEXITY_MARKERS):
            return "complex"
        if any(m in request_l for m in ("analyse", "audit", "scan",
                                        "chasse", "revue")):
            return "medium"
        return "simple"

    # -- traitement -------------------------------------------------------
    def handle(self, request: str, skill: str,
               task: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Traite une demande de bout en bout, preuve à chaque étape."""
        # 1. Garde d'entrée : injection ?
        guard = assess(request)
        if not guard.safe:
            self.evidence.record("request_rejected", reason="injection",
                                score=guard.score)
            return {"ok": False, "status": "rejected",
                    "reason": "instructions suspectes neutralisées"}
        # 2. Classification
        complexity = self.classify(request)
        self.evidence.record("request_received", complexity=complexity)
        # 3. Décision adaptative (plan vs exécution)
        risk = self.policy.classify_risk((task or {}).get("action",
                                                          "execute_task"))
        plan = self.decision.decide((task or {}).get("action",
                                                     "execute_task"),
                                    risk, {"agent_health": "healthy"})
        if not plan.execute:
            self.memory.log_decision(actor="command-core",
                                     kind="plan_only",
                                     action=plan.action, risk=risk,
                                     payload=plan.to_dict())
            return {"ok": False, "status": "plan_only", "plan": plan.to_dict()}
        # 4. Exécution
        task = dict(task or {})
        task.setdefault("action", "execute_task")
        try:
            outcome = self.orchestrator.run_task(skill, task)
        except NoAgentFound as exc:
            self.evidence.record("no_agent", skill=skill)
            return {"ok": False, "status": "no_agent", "error": str(exc)}
        # 5. Apprentissage prédictif des signaux
        if outcome.get("ok"):
            self.predictive.observe(f"skill:{skill}", weight=0.2)
        else:
            self.predictive.observe(f"skill:{skill}", weight=1.0)
        return {"ok": outcome.get("ok", False), "status": "dispatched",
                "complexity": complexity, "outcome": outcome}
