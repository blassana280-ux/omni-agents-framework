"""Évaluateur d'agents : verdicts factuels, synthèses, export JSON."""

from __future__ import annotations

import json

from cf100.agents.base import CyberAgent
from cf100.core.evaluation import AgentEvaluator


def _agent(registry, policy_engine, evidence, memory, agent_id):
    return CyberAgent(registry.by_id(agent_id), evidence, memory,
                      policy_engine, provider=lambda t: "ok")


def test_inactive_agent_reported_honestly(registry, policy_engine,
                                           evidence, memory):
    evaluator = AgentEvaluator(registry, agents={})
    report = evaluator.evaluate_agent("CI-001")
    assert report["verdict"] == "inactif"
    assert report["tasks_done"] == 0
    assert report["state"] == "dormant"
    assert report["success_rate"] is None


def test_operational_agent(registry, policy_engine, evidence, memory):
    agent = _agent(registry, policy_engine, evidence, memory, "CI-001")
    agent.activate()
    agent.execute({"action": "read_file"})
    report = AgentEvaluator(registry, agents={"CI-001": agent}) \
        .evaluate_agent("CI-001")
    assert report["tasks_done"] == 1
    assert report["success_rate"] == 1.0
    assert report["verdict"] == "opérationnel"


def test_watch_and_failing_agents(registry, policy_engine, evidence, memory):
    ok_agent = _agent(registry, policy_engine, evidence, memory, "CI-001")
    ok_agent.activate()
    ok_agent.execute({"action": "read_file"})
    fail_agent = _agent(registry, policy_engine, evidence, memory, "VR-001")
    fail_agent.activate()
    fail_agent.provider = lambda t: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        fail_agent.execute({"action": "scan_dependencies"})
    except RuntimeError:
        pass
    evaluator = AgentEvaluator(registry, agents={
        "CI-001": ok_agent, "VR-001": fail_agent})
    verdicts = {e["id"]: e["verdict"] for e in evaluator.report()["agents"]}
    assert verdicts["CI-001"] == "opérationnel"
    assert verdicts["VR-001"] == "défaillant"
    summary = evaluator.report()["summary"]
    assert summary["total"] == 100
    assert summary["inactif"] == 98


def test_export_writes_json(registry, tmp_path):
    out = tmp_path / "eval.json"
    path = AgentEvaluator(registry).export(out)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["agents"]) == 100
    assert set(data["divisions"]) == {"CI", "TH", "VR", "DP", "IR", "MA",
                                      "NS", "AS", "AI", "AC"}
