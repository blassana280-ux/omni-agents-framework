"""Orchestrateur : routage par compétence, fallbacks, vagues, conflits."""

from __future__ import annotations

import pytest

from cf100.agents.base import CyberAgent
from cf100.core.conflict import Finding, resolve
from cf100.core.orchestrator import NoAgentFound, Orchestrator


def _build_agents(registry, policy_engine, evidence, memory, provider):
    return {
        spec.id: CyberAgent(spec, evidence, memory, policy_engine,
                            provider=provider)
        for spec in registry.agents
    }


def test_routing_selects_right_division(registry, evidence, memory,
                                        policy_engine):
    orch = Orchestrator(
        _build_agents(registry, policy_engine, evidence, memory,
                      provider=lambda t: "ok"), evidence)
    picked = orch.select("phishing-analysis")
    assert picked[0].spec.id.startswith("DP-")


def test_unknown_skill_never_simulated(registry, evidence, memory,
                                        policy_engine):
    orch = Orchestrator(
        _build_agents(registry, policy_engine, evidence, memory,
                      provider=lambda t: "ok"), evidence)
    with pytest.raises(NoAgentFound):
        orch.select("compétence-inexistante-xyz")


def test_fallback_used_when_primary_denied(registry, evidence, memory,
                                           policy_engine):
    # MA-006 (Ransomware Analyst, supervised) : une action moyenne
    # (run_static_analysis) exige une validation ; son fallback MA-002
    # (autonomous) doit prendre le relais avec la même tâche.
    agents = _build_agents(registry, policy_engine, evidence, memory,
                           provider=lambda t: "fait")
    orch = Orchestrator(agents, evidence)
    outcome = orch.run_task("ransomware-analysis",
                            {"action": "run_static_analysis"})
    assert outcome["ok"] is True
    assert outcome.get("fallback_for") == "MA-006"
    assert outcome["agent"] == "MA-002"


def test_wave_runs_in_parallel(registry, evidence, memory, policy_engine):
    orch = Orchestrator(
        _build_agents(registry, policy_engine, evidence, memory,
                      provider=lambda t: t["action"]), evidence,
        max_workers=4)
    tasks = [
        {"skill": "osint", "task": {"action": "read_file"}},
        {"skill": "phishing-analysis", "task": {"action": "read_file"}},
        {"skill": "sbom", "task": {"action": "read_file"}},
        {"skill": "dns-security", "task": {"action": "read_file"}},
    ]
    results = orch.run_wave(tasks)
    assert len(results) == 4
    assert all(r["ok"] for r in results)


def test_conflict_resolution_by_evidence():
    findings = [
        Finding("TH-001", "malware-family", "RansomwareX", 1, True, 2),
        Finding("MA-002", "malware-family", "RansomwareY", 3, True, 2),
    ]
    verdict = resolve(findings)
    assert verdict["resolved"] is True
    assert verdict["winners"]["malware-family"] == "MA-002"


def test_conflict_unresolved_on_perfect_tie():
    findings = [
        Finding("TH-001", "entry-point", "phishing", 2, True, 2),
        Finding("TH-002", "entry-point", "vpn", 2, True, 2),
    ]
    verdict = resolve(findings)
    assert verdict["resolved"] is False
    assert "entry-point" in verdict["unresolved"]
