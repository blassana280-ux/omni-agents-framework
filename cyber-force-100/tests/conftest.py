"""Fixtures communes des tests Cyber Force 100."""

from __future__ import annotations

import pytest

from cf100.agents.registry import load_registry, load_policies
from cf100.core.evidence import EvidenceEngine
from cf100.memory.store import MemoryStore
from cf100.memory.tiers import MemoryTiers
from cf100.security.policy import ApprovalLedger, PolicyEngine


@pytest.fixture(scope="session")
def registry():
    """Registre complet (10 divisions, 100 agents) chargé une fois."""
    return load_registry()


@pytest.fixture(scope="session")
def policies():
    return load_policies()


@pytest.fixture()
def evidence(tmp_path):
    return EvidenceEngine(tmp_path / "evidence.jsonl")


@pytest.fixture()
def store(tmp_path):
    return MemoryStore(tmp_path / "memory.db")


@pytest.fixture()
def memory(store):
    return MemoryTiers(store)


@pytest.fixture()
def ledger(tmp_path):
    return ApprovalLedger(tmp_path / "approvals.json")


@pytest.fixture()
def policy_engine(policies, ledger):
    return PolicyEngine(policies, ledger)
