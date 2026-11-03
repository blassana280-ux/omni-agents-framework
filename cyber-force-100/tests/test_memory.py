"""Mémoire : persistance, quatre niveaux, contrôle d'accès, savoir validé."""

from __future__ import annotations

import pytest

from cf100.memory.store import MemoryStore
from cf100.memory.tiers import MemoryAccessDenied, MemoryTiers


def test_persistence_across_instances(tmp_path):
    db = tmp_path / "memory.db"
    MemoryStore(db).set("individual", "CI-001", "veille", {"last": "october"})
    reloaded = MemoryTiers(MemoryStore(db))
    assert reloaded.recall_individual("CI-001", "veille") == \
        {"last": "october"}


def test_individual_memory_isolation(memory):
    memory.remember_individual("CI-001", "notes", "source A")
    assert memory.recall_individual("CI-001", "notes") == "source A"
    with pytest.raises(MemoryAccessDenied):
        memory.recall_individual("CI-001", "notes", requester="TH-001")


def test_collective_write_requires_validation(memory, store):
    with pytest.raises(MemoryAccessDenied):
        # un agent ne peut pas écrire directement dans la mémoire collective
        memory.write_collective("tactique-x", "savoir", authorizer="CI-001")
    # cycle complet : proposition -> test -> validation humaine -> diffusion
    kid = store.propose_knowledge("TH-001", "IOC cluster détecté")
    store.set_knowledge_status(kid, "tested")
    store.set_knowledge_status(kid, "validated")
    memory.promote_validated(kid, "tactique-x", "savoir")
    assert memory.read_collective("tactique-x") == "savoir"


def test_unvalidated_knowledge_never_diffused(memory, store):
    kid = store.propose_knowledge("IR-009", "enseignement post-incident")
    store.set_knowledge_status(kid, "tested")  # pas encore validé
    with pytest.raises(MemoryAccessDenied):
        memory.promote_validated(kid, "lecon", "contenu")


def test_technical_memory_scope(memory):
    with pytest.raises(MemoryAccessDenied):
        memory.write_technical("runbook", "étapes", scope_ok=False)
    memory.write_technical("runbook", "étapes", scope_ok=True)
    assert memory.read_technical("runbook") == "étapes"


def test_decision_log_append_only(memory):
    memory.log_decision("decision-engine", "auto", "scan_dependencies",
                        "medium", {"score": 1.5})
    entries = memory.decisions()
    assert entries[0]["action"] == "scan_dependencies"
    assert entries[0]["approved_by"] is None
