"""Knowledge Evolution : cycle complet contrôlé, validations humaines."""

from __future__ import annotations

import pytest

from cf100.core.knowledge import KnowledgeEvolution


def test_full_pipeline_to_collective_memory(store, memory, evidence):
    ke = KnowledgeEvolution(store, memory, evidence)
    kid = ke.pipeline(
        agent="TH-001",
        claim="Le cluster d'IOC 185.x cible nos VPN",
        evidence_refs=["evidence://hunt-42", "evidence://ioc-7"],
        test_outcome="pass",
        human_approver="Lassana Bah",
        key="hunt-vpn-cluster",
        value={"ioc": "185.x", "status": "surveillé"},
    )
    assert store.knowledge_status(kid) == "validated"
    assert memory.read_collective("hunt-vpn-cluster") == \
        {"ioc": "185.x", "status": "surveillé"}


def test_rejected_tests_never_reach_collective(store, memory, evidence):
    ke = KnowledgeEvolution(store, memory, evidence)
    kid = ke.propose("MA-002", "règle YARA faussement positive")
    ke.mark_tested(kid, "fail")
    assert store.knowledge_status(kid) == "rejected"
    with pytest.raises(ValueError):
        ke.validate(kid, "Lassana Bah")


def test_agent_cannot_self_validate(store, memory, evidence):
    ke = KnowledgeEvolution(store, memory, evidence)
    kid = ke.propose("CI-002", "nouvelle source fiable")
    ke.mark_tested(kid, "pass")
    with pytest.raises(ValueError):
        ke.validate(kid, "CI-002")  # un agent ne se valide jamais lui-même
    ke.validate(kid, "Lassana Bah")  # un humain oui
    assert store.knowledge_status(kid) == "validated"


def test_untested_proposal_cannot_be_validated(store, memory, evidence):
    ke = KnowledgeEvolution(store, memory, evidence)
    kid = ke.propose("IR-009", "enseignement post-incident")
    with pytest.raises(ValueError):
        ke.validate(kid, "Lassana Bah")  # tests obligatoires avant
