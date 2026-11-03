"""Remédiation autonome : étapes encadrées, blocage sur action dangereuse."""

from __future__ import annotations

from cf100.core.evidence import EvidenceEngine
from cf100.core.remediation import RemediationEngine, RemediationStep


def _engine(policy_engine, evidence):
    return RemediationEngine(policy_engine, evidence)


def test_allowed_playbook_runs_completely(registry, policy_engine, evidence,
                                           memory):
    engine = _engine(policy_engine, evidence)
    agent = registry.by_id("VR-001")  # autonomous, outils de scan
    steps = [
        RemediationStep("inventaire", "scan_dependencies",
                        executor=lambda: {"deps": 42}),
        RemediationStep("rapport", "write_doc",
                        executor=lambda: "rapport.md"),
    ]
    outcome = engine.run_playbook(agent, "dep-audit", steps)
    assert outcome["status"] == "done"
    assert all(r["status"] == "done" for r in outcome["results"])


def test_dangerous_step_blocks_playbook(registry, policy_engine, evidence):
    engine = _engine(policy_engine, evidence)
    agent = registry.by_id("DP-001")  # hardening, assisted
    executed = []
    steps = [
        RemediationStep("analyse", "read_file",
                        executor=lambda: executed.append("analyse")),
        # action critique hors validation humaine :
        RemediationStep("déploiement", "deploy_production",
                        executor=lambda: executed.append("deploy")),
    ]
    outcome = engine.run_playbook(agent, "hardening", steps)
    assert outcome["status"] == "blocked"
    assert outcome["needs_human_approval"] == "deploy_production"
    assert executed == ["analyse"]  # jamais exécuté au-delà du blocage
    kinds = [e["kind"] for e in evidence.entries()]
    assert "remediation_blocked" in kinds


def test_medium_step_blocked_for_supervised_agent(registry, policy_engine,
                                                  evidence):
    engine = _engine(policy_engine, evidence)
    agent = registry.by_id("IR-004")  # supervised
    steps = [RemediationStep("journal", "write_doc",
                             executor=lambda: "notes")]
    outcome = engine.run_playbook(agent, "containment-notes", steps)
    assert outcome["status"] == "blocked"
