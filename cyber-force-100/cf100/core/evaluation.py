"""Agent Evaluator — évaluation honnête, agent par agent, division par division.

Les verdicts ne portent QUE sur des faits observés : tâches exécutées,
échecs, état courant. Un agent qui n'a jamais tourné est « inactif »,
pas « opérationnel » — aucun optimisme, aucune invention.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf100.agents.base import CyberAgent
from cf100.agents.registry import Registry

VERDICTS = ("opérationnel", "à surveiller", "inactif", "défaillant")


class AgentEvaluator:
    """Produit le rapport d'évaluation des agents CF100."""

    def __init__(self, registry: Registry,
                 agents: Optional[Dict[str, CyberAgent]] = None,
                 out_dir: Optional[Path] = None):
        self.registry = registry
        self.agents = agents or {}
        self.out_dir = Path(out_dir) if out_dir else None

    # -- un agent -------------------------------------------------------
    def evaluate_agent(self, agent_id: str) -> Dict[str, Any]:
        spec = self.registry.by_id(agent_id)
        if spec is None:
            raise ValueError(f"agent inconnu : {agent_id}")
        agent = self.agents.get(agent_id)
        tasks_done = agent.tasks_done if agent else 0
        tasks_failed = agent.tasks_failed if agent else 0
        state = agent.state.value if agent else "dormant"
        total = tasks_done + tasks_failed
        success_rate = round(tasks_done / total, 3) if total else None
        if tasks_failed and tasks_done == 0:
            verdict = "défaillant"
        elif tasks_done == 0 and tasks_failed == 0:
            verdict = "inactif"
        elif tasks_failed:
            verdict = "à surveiller"
        else:
            verdict = "opérationnel"
        return {
            "id": spec.id,
            "name": spec.name,
            "division": spec.division_code,
            "state": state,
            "autonomy": spec.autonomy.value,
            "tasks_done": tasks_done,
            "tasks_failed": tasks_failed,
            "success_rate": success_rate,
            "verdict": verdict,
        }

    # -- rapport complet --------------------------------------------------
    def report(self) -> Dict[str, Any]:
        per_agent = [self.evaluate_agent(a.id) for a in self.registry]
        by_division: Dict[str, Dict[str, int]] = {}
        for entry in per_agent:
            div = by_division.setdefault(
                entry["division"],
                {"agents": 0, **{v: 0 for v in VERDICTS}})
            div["agents"] += 1
            div[entry["verdict"]] += 1
        summary = {v: 0 for v in VERDICTS}
        for entry in per_agent:
            summary[entry["verdict"]] += 1
        return {
            "agents": per_agent,
            "divisions": by_division,
            "summary": {
                "total": len(per_agent),
                **summary,
            },
        }

    # -- export ----------------------------------------------------------
    def export(self, path: Optional[Path] = None) -> Path:
        """Écrit le rapport d'évaluation en JSON (dossier data par défaut)."""
        if path is None:
            from cf100.config import data_dir
            base = self.out_dir if self.out_dir else data_dir()
            path = base / "evaluation.json"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.report(), indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        return path
