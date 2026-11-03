"""Loading and validating the agent / skill / routing registries.

The registries are plain JSON so the framework has zero third-party
dependencies. ``Registry.validate()`` is the gate that prevents the network from
referencing an agent, skill or specialty that does not exist — the exact class
of bug that produced the broken ``optimiser-mes-agents-IA`` reference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Agent, Skill

REGISTRY_FILES = ("agents.json", "skills.json", "routing.json", "permissions.json")


class RegistryError(RuntimeError):
    pass


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RegistryError(f"missing registry file: {path}")
    with path.open(encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise RegistryError(f"invalid JSON in {path}: {exc}") from exc


class Registry:
    def __init__(
        self,
        agents: Dict[str, Agent],
        skills: Dict[str, Skill],
        routing: Dict[str, Any],
        permissions: Dict[str, Any],
        root: Optional[Path] = None,
    ) -> None:
        self.agents = agents
        self.skills = skills
        self.routing = routing
        self.permissions = permissions
        self.root = root

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, directory: str | Path) -> "Registry":
        d = Path(directory)
        raw_agents = _read(d / "agents.json")
        raw_skills = _read(d / "skills.json")
        routing = _read(d / "routing.json")
        permissions = _read(d / "permissions.json")

        agents: Dict[str, Agent] = {}
        for item in raw_agents["agents"]:
            agent = Agent.from_dict(item)
            if agent.id in agents:
                raise RegistryError(f"duplicate agent id: {agent.id}")
            agents[agent.id] = agent

        skills: Dict[str, Skill] = {}
        for item in raw_skills["skills"]:
            skill = Skill.from_dict(item)
            if skill.id in skills:
                raise RegistryError(f"duplicate skill id: {skill.id}")
            skills[skill.id] = skill

        return cls(agents, skills, routing, permissions, d)

    # -------------------------------------------------------------- queries
    @property
    def specialties(self) -> Dict[str, Any]:
        return self.routing["specialties"]

    def agents_for(self, specialty: str) -> List[Agent]:
        """Agents ranked for a specialty: declared primary first, then backups."""
        routing = self.specialties.get(specialty, {})
        primary = routing.get("agents", [])
        ordered: List[Agent] = []
        seen = set()
        for aid in primary:
            agent = self.agents.get(aid)
            if agent and aid not in seen:
                ordered.append(agent)
                seen.add(aid)
        # Any agent that declares the specialty but is not in the routing table
        # still counts as a fallback rather than being silently dropped.
        for agent in self.agents.values():
            if agent.id not in seen and specialty in agent.specialties:
                ordered.append(agent)
                seen.add(agent.id)
        return ordered

    def fallbacks(self, specialty: str, exclude: List[str] | None = None) -> List[str]:
        exclude = set(exclude or [])
        table = self.specialties.get(specialty, {})
        return [a for a in table.get("fallbacks", []) if a in self.agents and a not in exclude]

    def skills_for_specialty(self, specialty: str) -> List[Skill]:
        return [s for s in self.skills.values() if specialty in s.specialties]

    def search_skills(self, terms: List[str]) -> List[Skill]:
        lowered = [t.lower() for t in terms if t.strip()]
        hits: List[Skill] = []
        for skill in self.skills.values():
            haystack = " ".join([skill.id, skill.title, skill.source, skill.notes]).lower()
            if any(t in haystack for t in lowered):
                hits.append(skill)
        return hits

    def specialties_of(self, agent_id: str) -> List[str]:
        agent = self.agents.get(agent_id)
        return list(agent.specialties) if agent else []

    # ----------------------------------------------------------- validation
    def validate(self) -> List[str]:
        """Return every problem found. Empty list means the network is coherent."""
        problems: List[str] = []

        if not self.specialties:
            problems.append("routing.json declares no specialties")

        for sid, spec in self.specialties.items():
            if not spec.get("agents"):
                problems.append(f"specialty '{sid}' lists no agents")
            for aid in spec.get("agents", []) + spec.get("fallbacks", []):
                if aid not in self.agents:
                    problems.append(f"specialty '{sid}' references unknown agent '{aid}'")
            for aid in spec.get("agents", []):
                agent = self.agents.get(aid)
                if agent and sid not in agent.specialties:
                    problems.append(
                        f"agent '{aid}' is routed for '{sid}' but does not declare that specialty"
                    )

        covered = set()
        for agent in self.agents.values():
            if not agent.specialties:
                problems.append(f"agent '{agent.id}' declares no specialties")
            if not agent.provenance:
                problems.append(f"agent '{agent.id}' has no provenance (reuse must be documented)")
            for sid in agent.specialties:
                if sid not in self.specialties:
                    problems.append(f"agent '{agent.id}' declares unknown specialty '{sid}'")
                covered.add(sid)
            for skid in agent.skills:
                if skid not in self.skills:
                    problems.append(f"agent '{agent.id}' references unknown skill '{skid}'")

        for sid in self.specialties:
            if sid not in covered:
                problems.append(f"specialty '{sid}' has no agent declaring it")

        # Every specialty named in the mission matrix must exist somewhere.
        for sid in self.routing.get("required_specialties", []):
            if sid not in self.specialties:
                problems.append(f"required specialty missing from routing: '{sid}'")

        perms = self.permissions
        if "defaults" not in perms:
            problems.append("permissions.json has no defaults block")
        for aid in perms.get("agents", {}):
            if aid not in self.agents:
                problems.append(f"permissions.json references unknown agent '{aid}'")

        for agent in self.agents.values():
            allow = self.permissions.get("agents", {}).get(agent.id, {}).get("allowed_tools")
            if allow is None:
                problems.append(f"no explicit tool permissions for agent '{agent.id}'")

        return problems
