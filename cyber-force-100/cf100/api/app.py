"""API FastAPI de Cyber Force 100 (Phase 1 : lecture + statut).

L'API est optionnelle (extra `api`) ; le cœur fonctionne sans elle.
Points d'entrée :
- GET /health         : état global (audit léger) ;
- GET /divisions      : 10 divisions et leurs agents ;
- GET /agents/{id}    : profil détaillé d'un agent ;
- GET /agents         : les 100 agents (résumé) ;
- GET /evidence       : état de la chaîne de preuves ;
- POST /tasks         : soumet une tâche au Command Core.
"""

from __future__ import annotations

from typing import Any, Dict

from cf100.agents.registry import Registry, load_registry


def create_app(registry: Registry | None = None):
    """Fabrique de l'application FastAPI (import différé)."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "extra manquant : pip install '.[api]'") from exc

    registry = registry if registry is not None else load_registry()

    app = FastAPI(
        title="Cyber Force 100",
        description="Plateforme de cybersécurité défensive — "
                    "100 agents, 10 divisions, autonomie encadrée.",
        version="0.1.0",
    )

    class TaskIn(BaseModel):
        skill: str
        request: str = ""
        action: str = "execute_task"
        context: Dict[str, Any] = {}

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "divisions": len(registry.divisions),
            "agents": len(registry),
        }

    @app.get("/divisions")
    def divisions() -> Any:
        return [
            {"code": d.code, "id": d.id, "name": d.name,
             "purpose": d.purpose,
             "agents": [{"id": a.id, "name": a.name} for a in d.agents]}
            for d in registry.divisions
        ]

    @app.get("/agents")
    def agents() -> Any:
        return [a.to_dict() for a in registry]

    @app.get("/agents/{agent_id}")
    def agent_detail(agent_id: str) -> Any:
        spec = registry.by_id(agent_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="agent inconnu")
        return spec.to_dict()

    @app.get("/evidence")
    def evidence() -> Dict[str, Any]:
        from cf100.core.evidence import EvidenceEngine
        return EvidenceEngine().verify()

    @app.post("/tasks")
    def submit_task(task: TaskIn) -> Dict[str, Any]:
        from cf100.agents.base import CyberAgent
        from cf100.core.command import CommandCore
        from cf100.core.decision import DecisionEngine
        from cf100.core.evidence import EvidenceEngine
        from cf100.core.orchestrator import Orchestrator
        from cf100.core.predictive import PredictiveEngine
        from cf100.memory.tiers import MemoryTiers
        from cf100.security.policy import PolicyEngine

        ev = EvidenceEngine()
        mem = MemoryTiers()
        pol = PolicyEngine(registry.policies)
        agents = {}
        for spec in registry.agents:
            agents[spec.id] = CyberAgent(
                spec, ev, mem, pol, provider=None)
        orch = Orchestrator(agents, ev)
        core = CommandCore(orch, pol, ev, mem,
                           DecisionEngine(memory=mem),
                           PredictiveEngine())
        try:
            outcome = core.handle(
                task.request or task.skill,
                task.skill,
                {"action": task.action, "context": task.context},
            )
        except Exception as exc:  # refus explicite, jamais masqué
            raise HTTPException(status_code=422, detail=str(exc))
        return outcome

    return app
