"""Modèles de données des agents et divisions Cyber Force 100."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class Autonomy(str, Enum):
    """Niveau d'autonomie d'un agent.

    - autonomous : exécute seul les tâches de son niveau de risque.
    - assisted   : produit un plan, un humain valide l'exécution.
    - supervised : chaque action est relue avant exécution.
    """

    AUTONOMOUS = "autonomous"
    ASSISTED = "assisted"
    SUPERVISED = "supervised"


class RiskClass(str, Enum):
    """Classe de risque des actions qu'un agent peut entreprendre."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentState(str, Enum):
    """Cycle de vie d'un agent (base réelle, pas décorative)."""

    DORMANT = "dormant"          # déclaré, pas encore activé
    ACTIVE = "active"            # opérationnel
    EXECUTING = "executing"      # tâche en cours
    AWAITING_APPROVAL = "awaiting_approval"  # bloqué sur validation humaine
    DEGRADED = "degraded"        # échecs répétés ou heartbeat expiré
    STOPPED = "stopped"          # désactivé explicitement


@dataclass
class AgentSpec:
    """Spécification déclarative d'un agent, chargée depuis le registre."""

    id: str
    name: str
    division_code: str
    division: str
    mission: str
    skills: List[str]
    tools: List[str]
    allowed_scopes: List[str] = field(default_factory=list)
    denied_actions: List[str] = field(default_factory=list)
    activation: List[str] = field(default_factory=list)
    autonomy: Autonomy = Autonomy.SUPERVISED
    risk_class: RiskClass = RiskClass.LOW
    fallback: str = ""
    dynamic: bool = False        # agent temporaire créé à la demande

    @classmethod
    def from_dict(cls, data: Dict[str, Any], division_code: str,
                  division_name: str, dynamic: bool = False) -> "AgentSpec":
        perms = data.get("permissions", {}) or {}
        return cls(
            id=data["id"],
            name=data["name"],
            division_code=division_code,
            division=division_name,
            mission=data["mission"],
            skills=list(data.get("skills", [])),
            tools=list(data.get("tools", [])),
            allowed_scopes=list(perms.get("allowed_scopes", [])),
            denied_actions=list(perms.get("denied_actions", [])),
            activation=list(data.get("activation", [])),
            autonomy=Autonomy(data.get("autonomy", "supervised")),
            risk_class=RiskClass(data.get("risk_class", "low")),
            fallback=data.get("fallback", ""),
            dynamic=dynamic,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "division": self.division_code,
            "division_name": self.division,
            "mission": self.mission,
            "skills": self.skills,
            "tools": self.tools,
            "permissions": {
                "allowed_scopes": self.allowed_scopes,
                "denied_actions": self.denied_actions,
            },
            "activation": self.activation,
            "autonomy": self.autonomy.value,
            "risk_class": self.risk_class.value,
            "fallback": self.fallback,
            "dynamic": self.dynamic,
        }


@dataclass
class Division:
    """Une des 10 divisions de Cyber Force 100."""

    code: str
    id: str
    name: str
    purpose: str
    agents: List[AgentSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Division":
        div = cls(
            code=data["code"],
            id=data["id"],
            name=data["name"],
            purpose=data.get("purpose", ""),
        )
        div.agents = [
            AgentSpec.from_dict(a, div.code, div.name)
            for a in data.get("agents", [])
        ]
        return div
