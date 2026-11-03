"""Moteurs décisionnel et prédictif : déterminisme, apprentissage encadré."""

from __future__ import annotations

from cf100.core.decision import DecisionEngine
from cf100.core.predictive import PredictiveEngine


def test_low_risk_executes():
    engine = DecisionEngine()
    plan = engine.decide("read_file", "low", {"agent_health": "healthy"})
    assert plan.execute


def test_critical_never_executes_without_approval():
    engine = DecisionEngine()
    plan = engine.decide("merge_pr", "critical", {"agent_health": "healthy"})
    assert not plan.execute


def test_degraded_agent_downgrades_execution():
    engine = DecisionEngine()
    plan = engine.decide("run_tests", "medium",
                         {"agent_health": "degraded"})
    assert not plan.execute


def test_human_approval_swings_decision():
    engine = DecisionEngine()
    plan = engine.decide("open_pr", "high",
                         {"agent_health": "healthy",
                          "human_approved": True})
    assert plan.execute


def test_decisions_deterministic():
    engine = DecisionEngine()
    ctx = {"agent_health": "healthy"}
    a = engine.decide("scan_iac", "medium", ctx)
    b = engine.decide("scan_iac", "medium", ctx)
    assert a.score == b.score and a.execute == b.execute


def test_learning_gated_by_validation():
    engine = DecisionEngine()
    before = dict(engine.weights)
    # retour NON validé : aucun changement de comportement
    engine.learn({"validated": False,
                  "signals": [("risk_high", -1.0)]})
    assert engine.weights == before
    # retour validé : ajustement traçable
    engine.learn({"validated": True,
                  "signals": [("risk_high", -1.0)], "delta": 0.2})
    assert engine.weights["risk_high"] != before["risk_high"]


def test_predictive_ewma_rises_with_events():
    engine = PredictiveEngine()
    for _ in range(5):
        engine.observe("skill:malware-triage", weight=1.0)
    score = engine.score("skill:malware-triage")
    assert score["count"] == 5
    assert score["ewma"] > 0.5
    assert score["trend"] == "rising"


def test_predictive_confidence_requires_evidence():
    engine = PredictiveEngine()
    engine.observe("skill:x", weight=1.0)
    assert engine.score("skill:x")["confidence"] == "low"


def test_predictive_alert_threshold():
    engine = PredictiveEngine()
    for _ in range(10):
        engine.observe("division:IR", weight=1.0)
    assert "division:IR" in engine.alert_threshold(0.5)
