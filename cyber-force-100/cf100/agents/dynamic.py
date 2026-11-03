"""Fabrique d'agents dynamiques — créés selon les besoins, encadrés.

Un agent dynamique complète la force permanente sans jamais la remplacer :
- identifiant DYN-<horodatage>-<slug>, jamais persistant par défaut ;
- mêmes invariants que les agents permanents (outils en liste blanche,
  autonomie limitée, validation de registre) ;
- durée de vie bornée : il est retiré après sa mission.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict

from cf100.agents.models import AgentSpec, Autonomy, RiskClass
from cf100.agents.registry import Registry, RegistryError

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def make_dynamic_spec(need: str, mission: str, skills, tools,
                      risk_class: str = "low",
                      autonomy: str = "assisted") -> AgentSpec:
    """Construit la spécification d'un agent dynamique pour un besoin donné.

    Par défaut : autonomie assistée et risque faible — un agent dynamique
    ne peut pas être plus autonome qu'un agent permanent sans validation.
    """
    slug = _SLUG_RE.sub("-", need.lower()).strip("-")[:24] or "ad-hoc"
    agent_id = f"DYN-{int(time.time())}-{slug}"
    return AgentSpec(
        id=agent_id,
        name=f"Dynamic — {need}",
        division_code="DYN",
        division="Agents dynamiques",
        mission=mission,
        skills=list(skills),
        tools=list(tools),
        allowed_scopes=["task:execute"],
        denied_actions=["write_main", "delete_data", "change_permissions"],
        activation=[need],
        autonomy=Autonomy(autonomy),
        risk_class=RiskClass(risk_class),
        fallback="",
        dynamic=True,
    )


def spawn_dynamic_agent(registry: Registry, need: str, mission: str,
                        skills, tools, **kwargs) -> AgentSpec:
    """Crée, valide et enregistre un agent dynamique dans le registre."""
    spec = make_dynamic_spec(need, mission, skills, tools, **kwargs)
    try:
        registry.register_dynamic(spec)
    except RegistryError:
        raise
    return spec
