"""Cycle de vie des agents : états, provider réel, refus jamais simulé."""

from __future__ import annotations

import pytest

from cf100.agents.base import ActionDenied, CyberAgent
from cf100.agents.health import HealthMonitor
from cf100.agents.models import AgentState


def _agent(registry, policy_engine, evidence, memory, provider=None):
    spec = registry.by_id("CI-001")
    return CyberAgent(spec, evidence, memory, policy_engine,
                      provider=provider)


def test_lifecycle_activation(evidence, memory, policy_engine, registry):
    agent = _agent(registry, policy_engine, evidence, memory)
    assert agent.state == AgentState.DORMANT
    agent.activate()
    assert agent.state == AgentState.ACTIVE
    assert agent.last_heartbeat > 0


def test_execute_with_provider_records_evidence(evidence, memory,
                                               policy_engine, registry):
    agent = _agent(registry, policy_engine, evidence, memory,
                   provider=lambda task: {"found": 3})
    agent.activate()
    result = agent.execute({"action": "read_file"})
    assert result == {"found": 3}
    assert agent.tasks_done == 1
    kinds = [e["kind"] for e in evidence.entries()]
    assert "task_start" in kinds and "task_done" in kinds


def test_no_provider_never_simulated(evidence, memory, policy_engine,
                                     registry):
    agent = _agent(registry, policy_engine, evidence, memory)
    agent.activate()
    with pytest.raises(ActionDenied):
        agent.execute({"action": "read_file"})
    assert agent.tasks_done == 0
    assert agent.tasks_failed == 0  # refus, pas d'échec d'exécution
    assert any(e["kind"] == "task_refused" for e in evidence.entries())


def test_dangerous_action_blocks_agent(evidence, memory, policy_engine,
                                       registry):
    agent = _agent(registry, policy_engine, evidence, memory,
                   provider=lambda task: "ok")
    agent.activate()
    with pytest.raises(ActionDenied):
        agent.execute({"action": "delete_data"})
    assert agent.state == AgentState.AWAITING_APPROVAL
    assert agent.tasks_done == 0


def test_agent_individual_memory_roundtrip(evidence, memory, policy_engine,
                                           registry):
    agent = _agent(registry, policy_engine, evidence, memory)
    agent.remember("last_ioc", "1.2.3.4")
    assert agent.recall("last_ioc") == "1.2.3.4"


def test_health_monitor_degrades_silent_agent(evidence, memory,
                                              policy_engine, registry):
    monitor = HealthMonitor(timeout_s=0.05)
    agent = _agent(registry, policy_engine, evidence, memory)
    agent.activate()
    monitor.watch(agent)
    import time
    time.sleep(0.06)
    report = monitor.check()
    assert agent.spec.id in report["degraded"]
    assert report["fallbacks"][agent.spec.id] == agent.spec.fallback
    # reprise : restart() rend l'agent sain
    assert monitor.restart(agent.spec.id) is True
    assert monitor.summary()["healthy"] == 1
