"""Quatre niveaux de mémoire avec contrôle d'accès.

- individuelle : chaque agent lit/écrit SA mémoire uniquement ;
- collective   : lecture pour tous, écriture réservée (savoir validé ou
                  Knowledge Evolution Engine) ;
- technique    : lecture pour tous, écriture réservée aux agents avec le
                  scope memory:technical:write ;
- décisions    : append-only, jamais effaçable par un agent.
"""

from __future__ import annotations

from typing import Any, Optional

from cf100.memory.store import MemoryStore


class MemoryAccessDenied(Exception):
    """Accès mémoire refusé — moindre privilège."""


class MemoryTiers:
    """Façade d'accès aux quatre niveaux de mémoire persistante."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store if store is not None else MemoryStore()

    # -- mémoire individuelle ----------------------------------------
    def remember_individual(self, agent_id: str, key: str, value: Any) -> None:
        self.store.set("individual", agent_id, key, value)

    def recall_individual(self, agent_id: str, key: str,
                          requester: Optional[str] = None) -> Optional[Any]:
        if requester is not None and requester != agent_id:
            raise MemoryAccessDenied(
                f"{requester} ne peut pas lire la mémoire individuelle "
                f"de {agent_id}")
        return self.store.get("individual", agent_id, key)

    # -- mémoire collective (écriture contrôlée) ----------------------
    def read_collective(self, key: str, owner: str = "shared") -> Optional[Any]:
        return self.store.get("collective", owner, key)

    def write_collective(self, key: str, value: Any, authorizer: str,
                         validated_kid: Optional[int] = None) -> None:
        """Écrit dans la mémoire collective seulement si le savoir est
        validé ( Knowledge Evolution Engine) ou l'autorisation humaine."""
        if not validated_kid:
            if not authorizer or authorizer.startswith(("DYN-", "CI-", "TH-",
                    "VR-", "DP-", "IR-", "MA-", "NS-", "AS-", "AI-", "AC-")):
                raise MemoryAccessDenied(
                    "écriture collective réservée aux savoirs validés "
                    "(k-id) ou à une validation humaine")
        if validated_kid:
            status = self.store.knowledge_status(validated_kid)
            if status != "validated":
                raise MemoryAccessDenied(
                    f"connaissance {validated_kid} non validée "
                    f"(statut={status}) — diffusion bloquée")
        self.store.set("collective", "shared", key, value)

    # -- mémoire technique --------------------------------------------
    def read_technical(self, key: str) -> Optional[Any]:
        return self.store.get("technical", "system", key)

    def write_technical(self, key: str, value: Any, scope_ok: bool) -> None:
        if not scope_ok:
            raise MemoryAccessDenied(
                "scope memory:technical:write requis pour écrire la "
                "mémoire technique")
        self.store.set("technical", "system", key, value)

    # -- historique des décisions -------------------------------------
    def log_decision(self, actor: str, kind: str, action: str, risk: str,
                     payload: dict, approved_by: Optional[str] = None) -> int:
        return self.store.log_decision(actor, kind, action, risk, payload,
                                       approved_by)

    def decisions(self, actor: Optional[str] = None,
                  limit: int = 50) -> list:
        return self.store.decisions(actor, limit)

    # -- savoir validé -> collectif ------------------------------------
    def promote_validated(self, kid: int, key: str, value: Any) -> None:
        """Promeut un savoir validé dans la mémoire collective."""
        self.write_collective(key, value, authorizer="knowledge-evolution",
                               validated_kid=kid)
