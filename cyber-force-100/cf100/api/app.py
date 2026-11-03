"""API FastAPI de Cyber Force 100.

L'API est optionnelle (extra `api`) ; le cœur fonctionne sans elle.
Points d'entrée :
- GET /health            : état global ;
- GET /divisions         : 10 divisions et leurs agents ;
- GET /agents            : les 100 agents (résumé) ;
- GET /agents/{id}       : profil détaillé d'un agent ;
- GET /evidence          : état de la chaîne de preuves ;
- GET /evidence/verify   : vérification explicite de la chaîne ;
- GET /evaluation        : rapport d'évaluation des agents ;
- GET /dashboard         : tableau de bord HTML embarqué (sans CDN) ;
- POST /tasks            : soumet une tâche au Command Core.

Authentification : si la variable d'environnement CF100_API_TOKEN est
définie, toutes les routes SAUF /health et /dashboard exigent l'en-tête
X-API-Token correspondant (statut 401 sinon). Sans la variable, l'API
reste ouverte — à ne pas exposer publiquement dans ce cas.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from cf100.agents.registry import Registry, load_registry


def create_app(registry: Registry | None = None):
    """Fabrique de l'application FastAPI (import différé)."""
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import HTMLResponse, JSONResponse
        from pydantic import BaseModel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "extra manquant : pip install '.[api]'") from exc

    registry = registry if registry is not None else load_registry()

    app = FastAPI(
        title="Cyber Force 100",
        description="Plateforme de cybersécurité défensive — "
                    "100 agents, 10 divisions, autonomie encadrée.",
        version="0.2.0",
    )

    OPEN_PATHS = ("/health", "/dashboard")

    @app.middleware("http")
    async def token_auth(request: Request, call_next):
        """Zero Trust applicatif : token exigé sur toutes les routes
        ouvertes au travail, sauf santé et tableau de bord."""
        expected = os.environ.get("CF100_API_TOKEN", "")
        if expected and request.url.path not in OPEN_PATHS:
            provided = request.headers.get("X-API-Token", "")
            if provided != expected:
                return JSONResponse(
                    {"detail": "en-tête X-API-Token manquant ou invalide"},
                    status_code=401)
        return await call_next(request)

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

    @app.get("/evidence/verify")
    def evidence_verify() -> Dict[str, Any]:
        from cf100.core.evidence import EvidenceEngine
        return EvidenceEngine().verify()

    @app.get("/evaluation")
    def evaluation() -> Dict[str, Any]:
        from cf100.core.evaluation import AgentEvaluator
        # Rapport honnête : sans agents en exécution, les verdicts sont
        # « inactif » — l'API n'affirme jamais un travail non fait.
        return AgentEvaluator(registry).report()

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        from cf100.api.dashboard import DASHBOARD_HTML
        return DASHBOARD_HTML

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
