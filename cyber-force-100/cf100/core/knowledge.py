"""Knowledge Evolution Engine — évolution des connaissances contrôlée.

Cycle obligatoire : proposal -> tests -> validation humaine -> diffusion
dans la mémoire collective. Aucune connaissance ne modifie le comportement
des agents sans passer par ce cycle, et chaque étape est historisée.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cf100.core.evidence import EvidenceEngine
from cf100.memory.store import MemoryStore
from cf100.memory.tiers import MemoryAccessDenied, MemoryTiers


class KnowledgeEvolution:
    """Gère le cycle de vie des connaissances de Cyber Force 100."""

    def __init__(self, store: MemoryStore,
                 memory: Optional[MemoryTiers] = None,
                 evidence: Optional[EvidenceEngine] = None):
        self.store = store
        self.memory = memory if memory is not None else MemoryTiers(store)
        self.evidence = evidence

    def propose(self, agent: str, claim: str,
                evidence_refs: Optional[List[str]] = None) -> int:
        """Un agent propose une nouvelle connaissance (jamais diffusée)."""
        kid = self.store.propose_knowledge(agent, claim, evidence_refs)
        if self.evidence is not None:
            self.evidence.record("knowledge_proposed", agent=agent,
                                 kid=kid)
        return kid

    def mark_tested(self, kid: int, test_outcome: str) -> str:
        """Consigne le résultat des tests sur la proposition."""
        status = self.store.knowledge_status(kid)
        if status != "proposed":
            raise ValueError(f"connaissance {kid} : transition interdite "
                             f"depuis {status}")
        self.store.set_knowledge_status(
            kid, "tested" if test_outcome == "pass" else "rejected")
        if self.evidence is not None:
            self.evidence.record("knowledge_tested", kid=kid,
                                 outcome=test_outcome)
        return self.store.knowledge_status(kid)

    def validate(self, kid: int, human_approver: str) -> str:
        """Validation humaine — seul chemin vers 'validated'.

        L'approbateur doit être humain : un identifiant d'agent est refusé.
        """
        if not human_approver or human_approver[:3] in (
                "CI-", "TH-", "VR-", "DP-", "IR-", "MA-", "NS-", "AS-",
                "AI-", "AC-") or human_approver.startswith(("DYN-", "omni-")):
            raise ValueError("la validation finale doit être humaine")
        status = self.store.knowledge_status(kid)
        if status != "tested":
            raise ValueError(f"connaissance {kid} : statut {status}, "
                             f"tests requis avant validation")
        self.store.set_knowledge_status(kid, "validated")
        if self.evidence is not None:
            self.evidence.record("knowledge_validated", kid=kid,
                                 approver=human_approver)
        return "validated"

    def promote(self, kid: int, key: str, value: Any) -> None:
        """Diffuse une connaissance validée dans la mémoire collective."""
        try:
            self.memory.promote_validated(kid, key, value)
        except MemoryAccessDenied:
            raise
        if self.evidence is not None:
            self.evidence.record("knowledge_promoted", kid=kid, key=key)

    def pipeline(self, agent: str, claim: str, evidence_refs: List[str],
                 test_outcome: str, human_approver: str,
                 key: str, value: Any) -> int:
        """Cycle complet en un appel — utilisé par les tests d'intégration."""
        kid = self.propose(agent, claim, evidence_refs)
        self.mark_tested(kid, test_outcome)
        self.validate(kid, human_approver)
        self.promote(kid, key, value)
        return kid
