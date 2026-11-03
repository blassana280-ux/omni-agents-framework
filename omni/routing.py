"""Specialty routing: classify a request, pick agents, build a squad.

The classifier is deterministic (keyword + weight scoring) on purpose: it is
auditable, testable offline, and cannot silently hallucinate a specialty. An
LLM-backed provider may later *refine* the classification, but the deterministic
path always remains available as the fallback.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .models import Assignment, Brief, Classification, Plan, Task
from .policy import Policy
from .registry import Registry


class MissingSpecialty(LookupError):
    """Raised when no agent can cover a required specialty."""

    def __init__(self, specialty: str, suggestions: List[str]) -> None:
        self.specialty = specialty
        self.suggestions = suggestions
        super().__init__(
            f"no agent covers specialty '{specialty}'; closest skills: "
            + (", ".join(suggestions) if suggestions else "(none in registry)")
        )


_WORD = re.compile(r"[a-z0-9+#_.\-]+")


def _tokens(text: str) -> List[str]:
    return _WORD.findall(text.lower())


class Router:
    def __init__(self, registry: Registry, policy: Optional[Policy] = None) -> None:
        self.registry = registry
        self.policy = policy or Policy(registry.permissions)
        self._triggers: Dict[str, float] = registry.routing.get("size_thresholds", {}) or {}

    # ---------------------------------------------------------- classify
    def classify(self, request: str) -> Classification:
        tokens = set(_tokens(request))
        scores: Dict[str, float] = {}
        for sid, spec in self.registry.specialties.items():
            triggers = [t.lower() for t in spec.get("triggers", [])]
            if not triggers:
                continue
            score = 0.0
            for trig in triggers:
                if " " in trig:
                    if trig in request.lower():
                        score += 1.5 * spec.get("weight", 1.0)
                elif trig in tokens:
                    score += 1.0 * spec.get("weight", 1.0)
            if score:
                scores[sid] = round(score, 3)

        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        selected = self._select_count(ranked, request)
        specialties = [sid for sid, _ in ranked[:selected]]
        size = self._size_for(len(specialties))
        if specialties:
            rationale = (
                f"{size}: {len(specialties)} specialties triggered ("
                + ", ".join(f"{s}={sc}" for s, sc in ranked[:selected])
                + ")"
            )
        else:
            rationale = "simple: no specialty trigger matched, defaulting to research-docs"
            specialties = ["research-docs"]
        return Classification(size=size, scores=dict(ranked), specialties=specialties, rationale=rationale)

    def _select_count(self, ranked: List[Tuple[str, float]], request: str) -> int:
        if not ranked:
            return 0
        thresholds = self.registry.routing.get("size_thresholds", {})
        min_score = thresholds.get("min_score", 1.0)
        keep = [sid for sid, sc in ranked if sc >= min_score] or [ranked[0][0]]
        max_complex = thresholds.get("max_squad", 8)
        explicit = thresholds.get("explicit_complex_markers", [])
        lowered = request.lower()
        complex_requested = any(m in lowered for m in explicit)
        # A multi-specialty request keeps up to 3 agents unless it is explicitly
        # flagged as complex, in which case the squad may grow to max_squad.
        return min(len(keep), max_complex if complex_requested else 3)

    @staticmethod
    def _size_for(count: int) -> str:
        if count <= 1:
            return "simple"
        if count <= 3:
            return "medium"
        return "complex"

    # ------------------------------------------------------------- select
    def select_agent(self, specialty: str, exclude: Optional[List[str]] = None) -> str:
        candidates = [
            a for a in self.registry.agents_for(specialty) if a.id not in set(exclude or [])
        ]
        if not candidates:
            terms = [specialty.replace("-", " "), specialty]
            suggestions = [s.id for s in self.registry.search_skills(terms)]
            raise MissingSpecialty(specialty, suggestions)
        # Rank: explicit routing order is already meaningful, then skill coverage.
        return candidates[0].id

    # --------------------------------------------------------------- plan
    def plan(self, request: str, max_tasks: Optional[int] = None) -> Plan:
        classification = self.classify(request)
        tasks: List[Task] = []
        unresolved: List[str] = []
        used_agents: List[str] = []
        chosen: Dict[str, str] = {}   # task id -> agent id (never re-derived)

        for idx, sid in enumerate(classification.specialties):
            try:
                agent_id = self.select_agent(sid, exclude=used_agents)
            except MissingSpecialty:
                unresolved.append(sid)
                continue
            used_agents.append(agent_id)
            spec = self.registry.specialties[sid]
            task_id = f"t{idx + 1}-{sid}"
            chosen[task_id] = agent_id
            template = spec.get("objective_template")
            objective = (
                template.format(request=request)
                if template
                else f"{spec.get('title', sid)} — for request: {request}"
            )
            tasks.append(
                Task(
                    id=task_id,
                    specialty=sid,
                    title=spec.get("title", sid),
                    objective=objective,
                    acceptance_criteria=spec.get("acceptance_criteria", []),
                )
            )

        if max_tasks:
            tasks = tasks[:max_tasks]

        # Dependencies: a reviewer task always depends on everything else, so it
        # runs in a later wave and grades real output rather than assumptions.
        review_sids = {"code-review", "testing-qa"}
        non_review = [t for t in tasks if t.specialty not in review_sids]
        review = [t for t in tasks if t.specialty in review_sids]
        for rt in review:
            rt.depends_on = [t.id for t in non_review]

        wave_of: Dict[str, int] = {}
        for task in tasks:  # tasks are already in a dependency-safe order
            wave_of[task.id] = 1 + max([wave_of.get(d, 0) for d in task.depends_on], default=0)

        assignments: List[Assignment] = []
        for task in tasks:
            agent_id = chosen[task.id]
            agent = self.registry.agents[agent_id]
            brief = Brief(
                task_id=task.id,
                agent_id=agent_id,
                specialty=task.specialty,
                objective=task.objective,
                acceptance_criteria=task.acceptance_criteria,
                allowed_tools=self.policy.allowed_tools(agent_id),
                boundaries=agent.boundaries,
                context={"request": request, "specialty": task.specialty},
            )
            assignments.append(Assignment(task=task, agent_id=agent_id, wave=wave_of[task.id], brief=brief))

        return Plan(
            request=request,
            classification=classification,
            tasks=tasks,
            assignments=assignments,
            squad=[a.agent_id for a in assignments],
            unresolved_specialties=unresolved,
        )

    # -------------------------------------------------------------- squad
    def squad_for_template(self, template: str) -> List[str]:
        tpl = self.registry.routing.get("squad_templates", {}).get(template)
        if not tpl:
            raise KeyError(f"unknown squad template: {template}")
        agents: List[str] = []
        for sid in tpl["specialties"]:
            agents.append(self.select_agent(sid, exclude=agents))
        return agents

    def _owns(self, agent_id: str, specialty: str) -> bool:
        return specialty in self.registry.specialties_of(agent_id)
