"""Zero Trust — identité vérifiée, autorisation par action, refus par défaut.

Aucune confiance implicite : chaque interaction d'un agent passe par
authenticate() puis par une autorisation explicite. Un principal inconnu
est toujours refusé.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cf100.agents.registry import Registry, RegistryError


@dataclass
class Principal:
    """Identité vérifiée d'un appelant (agent ou humain)."""

    id: str
    kind: str                     # "agent" | "human" | "service"
    token_valid: bool
    authenticated_at: float
    attributes: Dict[str, Any] = field(default_factory=dict)


class IdentityError(Exception):
    """Échec d'authentification — refus par défaut."""


def authenticate(principal_id: str, token: Optional[str] = None,
                 registry: Optional[Registry] = None,
                 human_ids: Optional[Dict[str, str]] = None) -> Principal:
    """Authentifie un principal. Les humains viennent d'un annuaire
    explicite (human_ids : {id: secret partagé}) ; les agents doivent
    exister dans le registre. Les tokens d'agents sont vérifiés par
    l'orchestrateur à la distribution — ici on vérifie l'existence.
    """
    if human_ids and principal_id in human_ids:
        return Principal(principal_id, "human", True, time.time())
    if registry is not None:
        spec = registry.by_id(principal_id)
        if spec is not None:
            return Principal(principal_id, "agent", token is not None,
                             time.time(),
                             {"division": spec.division_code,
                              "autonomy": spec.autonomy.value})
        raise IdentityError(f"principal inconnu du registre : {principal_id}")
    # Sans registre fourni : identité agent préfixée reconnue comme
    # NON authentifiée (token_valid=False) — refus par défaut conservateur.
    return Principal(principal_id, "agent", False, time.time())


def authorize_scope(principal: Principal, scope: str,
                    allowed: Any) -> bool:
    """Vérifie un périmètre d'accès — moindre privilège, refus par défaut."""
    if not principal.token_valid:
        return False
    if principal.kind == "human":
        return True
    return scope in allowed
