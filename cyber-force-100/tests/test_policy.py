"""Politiques : refus par défaut, validation humaine, plafonds d'autonomie."""

from __future__ import annotations

import pytest

from cf100.agents.models import Autonomy, RiskClass
from cf100.security.policy import PolicyEngine


def test_dangerous_action_denied_without_approval(registry, policy_engine):
    agent = registry.by_id("IR-004")
    # On force un profil qui possède l'outil pour isoler la règle
    agent.tools = list(agent.tools) + ["merge_pr"]
    decision = policy_engine.authorize(agent, "merge_pr", {})
    assert not decision.allowed
    assert decision.needs_approval
    agent.tools.remove("merge_pr")


def test_dangerous_action_allowed_after_human_approval(registry,
                                                       policy_engine,
                                                       ledger):
    ledger.approve("merge_pr", approver="Lassana Bah",
                   note="validation explicite")
    agent = registry.by_id("IR-004")
    agent.tools = list(agent.tools) + ["merge_pr"]
    decision = policy_engine.authorize(agent, "merge_pr", {})
    assert decision.allowed
    agent.tools.remove("merge_pr")


def test_ledger_rejects_agent_approval(ledger):
    with pytest.raises(ValueError):
        ledger.approve("delete_data", approver="IR-001")
    with pytest.raises(ValueError):
        ledger.approve("delete_data", approver="DYN-123-x")


def test_default_deny_unknown_tool(registry, policy_engine):
    agent = registry.by_id("CI-001")
    assert "force_push" not in agent.tools
    decision = policy_engine.authorize(agent, "force_push", {})
    assert not decision.allowed


def test_low_risk_auto_executes(registry, policy_engine):
    agent = registry.by_id("CI-001")
    decision = policy_engine.authorize(agent, "web_search", {})
    assert decision.allowed and not decision.needs_approval


def test_medium_risk_ceiling_by_autonomy(registry, policy_engine):
    # TH-001 est autonomous : scan_dependencies (medium) passe
    agent = registry.by_id("TH-001")
    assert "scan_dependencies" not in agent.tools  # outil non dans son profil
    agent.tools = list(agent.tools) + ["scan_dependencies"]
    decision = policy_engine.authorize(agent, "scan_dependencies", {})
    assert decision.allowed
    agent.tools.remove("scan_dependencies")
    # IR-004 est supervised : medium exige une validation
    agent = registry.by_id("IR-004")
    agent.tools = list(agent.tools) + ["scan_dependencies"]
    decision = policy_engine.authorize(agent, "scan_dependencies", {})
    assert not decision.allowed and decision.needs_approval
    agent.tools.remove("scan_dependencies")


def test_profile_denied_action_wins(registry, policy_engine):
    agent = registry.by_id("VR-003")
    assert "credential_harvest" in agent.denied_actions
    decision = policy_engine.authorize(agent, "credential_harvest", {})
    assert not decision.allowed


def test_high_risk_requires_approval(registry, policy_engine):
    agent = registry.by_id("AS-001")
    agent.tools = list(agent.tools) + ["open_pr"]
    decision = policy_engine.authorize(agent, "open_pr", {})
    # risque haut : jamais exécution directe, plan + validation humaine
    assert decision.needs_approval
    assert not decision.allowed
    agent.tools.remove("open_pr")


def test_risk_classification_consistency(policy_engine):
    for action in ("merge_pr", "force_push", "delete_repo", "write_main"):
        assert policy_engine.is_dangerous(action)
        assert policy_engine.classify_risk(action) == "critical"
    assert policy_engine.classify_risk("read_file") == "low"
