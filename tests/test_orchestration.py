"""Scenarios 3, 5, 6, 7, 10 — parallel execution, failure recovery,
arbitration, correction loop, traceability.

All orchestration logic below runs for real. The model backend is replaced by
``ScriptedProvider`` (an explicit test double, see tests/helpers.py); no test
here claims that an AI agent was executed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ScriptedProvider, failing, load_registry
from omni.executor import ManualProvider
from omni.models import ProviderResult
from omni.orchestrator import Orchestrator

COMPLEX = (
    "Refonte de bout en bout : API REST backend, interface React, tests, "
    "CI GitHub Actions, analyse des données"
)
SIMPLE = "Ajoute un endpoint REST pour lister les utilisateurs"
TWO_SPECIALTIES = "Ajoute un endpoint REST backend et une interface React"


class OrchestrationBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = load_registry(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def orchestrator(self, provider, **kwargs) -> Orchestrator:
        return Orchestrator(
            self.registry,
            provider,
            workspace=self.root,
            state_dir=self.root / ".omni",
            max_parallel= kwargs.pop("max_parallel", 4),
            retries=kwargs.pop("retries", 1),
            correction_rounds=kwargs.pop("correction_rounds", 2),
            **kwargs,
        )


class TestParallelExecution(OrchestrationBase):
    """Scenario 3 — several agents run in the same wave, really concurrently."""

    def test_wave_is_parallel_not_sequential(self) -> None:
        provider = ScriptedProvider(delay=0.30)
        orch = self.orchestrator(provider)
        record = orch.run(COMPLEX)

        waves = [e for e in record.trace if e["event"] == "wave"]
        self.assertTrue(waves, "no wave recorded")
        first = waves[0]
        self.assertGreaterEqual(first["size"], 4, first)
        self.assertGreater(len(set(first["tasks"])), 1)

        # Parallelism proof: wall time close to one task, well below the sum.
        self.assertGreater(first["serial_s"], 4 * 0.25, first)
        self.assertLess(first["wall_s"], first["serial_s"] * 0.75, first)

    def test_every_agent_in_wave_received_a_brief(self) -> None:
        provider = ScriptedProvider(delay=0.0)
        record = self.orchestrator(provider).run(COMPLEX)
        dispatched = {e["agent"] for e in record.trace if e["event"] == "dispatch"}
        self.assertEqual(dispatched, set(record.squad))
        for call in provider.calls:
            self.assertTrue(call["tools"], f"agent {call['agent']} got no tool list")

    def test_review_wave_runs_after_work_wave(self) -> None:
        record = self.orchestrator(ScriptedProvider()).run(COMPLEX)
        waves = [e for e in record.trace if e["event"] == "wave"]
        self.assertGreaterEqual(len(waves), 2)
        dispatch_wave = {e["task"]: e["wave"] for e in record.trace if e["event"] == "dispatch"}
        work = [t for t, w in dispatch_wave.items() if w == 1]
        review = [t for t, w in dispatch_wave.items() if w == 2]
        self.assertTrue(work and review, dispatch_wave)


class TestFailureRecovery(OrchestrationBase):
    """Scenario 5 — retry, then reassignment, then escalation."""

    def test_failure_is_retried_then_reassigned(self) -> None:
        provider = ScriptedProvider(script={"omni-backend": failing("omni-backend")})
        record = self.orchestrator(provider, retries=1).run(SIMPLE)

        attempts = [r for r in record.results if r.task_id.startswith("t1-")]
        self.assertEqual(len(attempts), 3, [(r.agent_id, r.status) for r in attempts])
        self.assertEqual([r.attempt for r in attempts], [1, 2, 3])
        self.assertEqual(attempts[0].agent_id, "omni-backend")
        self.assertEqual(attempts[1].agent_id, "omni-backend")
        self.assertEqual(attempts[2].agent_id, "omni-generalist")
        self.assertEqual(attempts[2].reassigned_from, "omni-backend")
        self.assertEqual(attempts[2].status, "ok")

        events = [e["event"] for e in record.trace]
        self.assertIn("retry", events)
        self.assertIn("reassign", events)
        # recovery produced a usable deliverable
        self.assertEqual(record.verdict, "READY", [f for f in record.findings if not f.passed])

    def test_total_failure_escalates_and_never_claims_success(self) -> None:
        provider = ScriptedProvider(
            script={
                "omni-backend": failing("omni-backend"),
                "omni-generalist": failing("omni-generalist"),
            }
        )
        record = self.orchestrator(provider, retries=1).run(SIMPLE)
        self.assertEqual(record.verdict, "NEEDS_WORK")
        self.assertIn("escalate", [e["event"] for e in record.trace])
        self.assertTrue(all(r.status == "failed" for r in record.results))
        self.assertTrue(any(f.gate == "completeness" and not f.passed for f in record.findings))

    def test_provider_exception_does_not_kill_the_run(self) -> None:
        def boom(brief):
            raise RuntimeError("provider crashed")

        record = self.orchestrator(ScriptedProvider(script={"omni-backend": boom})).run(SIMPLE)
        crashed = [r for r in record.results if "provider crashed" in (r.error or "")]
        self.assertTrue(crashed, "the provider exception was not recorded")
        self.assertFalse(any(r.executed for r in crashed))
        # the run survives and recovers through the fallback agent
        self.assertIn("reassign", [e["event"] for e in record.trace])
        self.assertEqual(record.verdict, "READY")


class TestArbitration(OrchestrationBase):
    """Scenario 6 — contradictory results are arbitrated, or flagged."""

    def test_more_evidence_wins(self) -> None:
        provider = ScriptedProvider(
            script={
                "omni-backend": [
                    ProviderResult(
                        status="ok",
                        summary="FastAPI chosen",
                        evidence=["bench:fastapi", "docs:fastapi"],
                        met_criteria=[],  # filled below by helper? no: explicit
                        claims={"framework": "fastapi"},
                        executed=True,
                        provider="scripted-double",
                    )
                ],
                "omni-frontend": [
                    ProviderResult(
                        status="ok",
                        summary="Next.js chosen",
                        evidence=["docs:next"],
                        claims={"framework": "nextjs"},
                        executed=True,
                        provider="scripted-double",
                    )
                ],
            }
        )
        # meet every criterion on both sides so only arbitration is at stake
        plan = self.orchestrator(provider).plan(TWO_SPECIALTIES)
        for assignment in plan.assignments:
            assignment.task.acceptance_criteria = []
        record = self.orchestrator(provider).run(TWO_SPECIALTIES, plan=plan)

        self.assertEqual(len(record.arbitrations), 1)
        arb = record.arbitrations[0]
        self.assertEqual(arb.topic, "framework")
        self.assertEqual(arb.winner_agent, "omni-backend")
        self.assertTrue(arb.resolved)
        self.assertIn("evidence_count", arb.rule)
        self.assertTrue(any(e["event"] == "arbitration" for e in record.trace))

    def test_tie_is_left_unresolved_and_fails_the_gate(self) -> None:
        def same_weight(agent: str, claim: str):
            return ProviderResult(
                status="ok",
                summary=f"{agent} says {claim}",
                evidence=["single-source"],
                claims={"format": claim},
                executed=True,
                provider="scripted-double",
            )

        provider = ScriptedProvider(
            script={
                "omni-backend": [same_weight("omni-backend", "json")],
                "omni-frontend": [same_weight("omni-frontend", "yaml")],
            }
        )
        plan = self.orchestrator(provider).plan(TWO_SPECIALTIES)
        for assignment in plan.assignments:
            assignment.task.acceptance_criteria = []
        record = self.orchestrator(provider).run(TWO_SPECIALTIES, plan=plan)

        self.assertEqual(len(record.arbitrations), 1)
        self.assertFalse(record.arbitrations[0].resolved)
        self.assertEqual(record.verdict, "NEEDS_WORK")
        self.assertTrue(any(f.gate == "arbitration" and not f.passed for f in record.findings))


class TestCorrectionLoop(OrchestrationBase):
    """Scenario 7 — an incomplete deliverable triggers a correction request."""

    def test_incomplete_deliverable_is_sent_back(self) -> None:
        def provider_fn(brief):
            met = list(brief.acceptance_criteria)
            if brief.attempt == 1:
                met = met[:-1]  # drop the last criterion on the first attempt
            return ProviderResult(
                status="ok",
                summary=f"attempt {brief.attempt}",
                evidence=[f"ev:{brief.attempt}"],
                met_criteria=met,
                executed=True,
                provider="scripted-double",
            )

        provider = ScriptedProvider(script={"omni-backend": provider_fn})
        record = self.orchestrator(provider, correction_rounds=2).run(SIMPLE)

        self.assertTrue(record.corrections, "no correction was requested")
        correction = record.corrections[0]
        self.assertEqual(correction.agent_id, "omni-backend")
        self.assertEqual(len(correction.missing_criteria), 1)
        self.assertEqual(correction.round, 1)

        # a correction message really went onto the bus
        bus_lines = (self.root / ".omni" / "bus.jsonl").read_text(encoding="utf-8").splitlines()
        kinds = [json.loads(l)["kind"] for l in bus_lines if l.strip()]
        self.assertIn("correction", kinds)

        # the corrected attempt carries the missing criterion in its brief
        corrected = [c for c in provider.calls if c["attempt"] == 2]
        self.assertTrue(corrected)
        self.assertEqual(len(corrected[0]["missing"]), 1)

        latest = record.by_task()
        self.assertEqual(latest["t1-backend-api"].attempt, 2)
        self.assertEqual(latest["t1-backend-api"].status, "ok")
        self.assertEqual(record.verdict, "READY", [f for f in record.findings if not f.passed])

    def test_persistently_incomplete_stays_needs_work(self) -> None:
        provider = ScriptedProvider(
            script={
                "omni-backend": [
                    ProviderResult(
                        status="ok",
                        summary="partial",
                        evidence=["ev"],
                        met_criteria=[],
                        executed=True,
                        provider="scripted-double",
                    )
                ]
            }
        )
        record = self.orchestrator(provider, correction_rounds=1).run(SIMPLE)
        self.assertEqual(record.verdict, "NEEDS_WORK")
        self.assertTrue(record.corrections)
        self.assertTrue(any(f.gate == "completeness" and not f.passed for f in record.findings))


class TestHonestExecution(OrchestrationBase):
    def test_manual_provider_never_claims_an_agent_ran(self) -> None:
        record = self.orchestrator(ManualProvider()).run(SIMPLE)
        self.assertTrue(record.results)
        for result in record.results:
            self.assertFalse(result.executed)
            self.assertEqual(result.status, "pending_human")
        self.assertEqual(record.verdict, "NEEDS_WORK")
        gate = next(f for f in record.findings if f.gate == "execution")
        self.assertFalse(gate.passed)
        self.assertIn("not executed", gate.detail)


class TestTraceability(OrchestrationBase):
    """Scenario 10 — every agent, tool and result is traceable."""

    def test_trace_records_the_whole_run(self) -> None:
        record = self.orchestrator(ScriptedProvider()).run(SIMPLE)

        events = [e["event"] for e in record.trace]
        for expected in ("plan", "policy", "dispatch", "result", "verdict"):
            self.assertIn(expected, events)

        # one dispatch + one result per task, with the agent and provider named
        dispatches = [e for e in record.trace if e["event"] == "dispatch"]
        results = [e for e in record.trace if e["event"] == "result"]
        self.assertEqual(len(dispatches), len(results))
        for entry in dispatches:
            self.assertIn(entry["agent"], self.registry.agents)
            self.assertEqual(entry["provider"], "scripted-double")
            self.assertIsInstance(entry["tools"], list)

        # tools actually consulted are traceable
        actions = {e["action"] for e in record.trace if e["event"] == "policy"}
        self.assertIn("execute_task", actions)

        # everything is persisted, and queryable after the fact
        run_file = self.root / ".omni" / "runs" / f"{record.run_id}.json"
        trace_file = self.root / ".omni" / "runs" / f"{record.run_id}.jsonl"
        self.assertTrue(run_file.is_file())
        self.assertTrue(trace_file.is_file())
        persisted = json.loads(run_file.read_text(encoding="utf-8"))
        self.assertEqual(persisted["run_id"], record.run_id)
        self.assertEqual(persisted["verdict"], record.verdict)
        self.assertEqual(len(persisted["results"]), len(record.results))
        trace_lines = [json.loads(l) for l in trace_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(trace_lines), len(record.trace))

        # the verdict is published to controlled shared memory
        memory = json.loads((self.root / ".omni" / "memory.json").read_text(encoding="utf-8"))
        entry = memory["entries"][f"shared::verdict:{record.run_id}"]
        self.assertEqual(entry["owner"], "omnibrain")
        self.assertEqual(entry["value"]["verdict"], record.verdict)

    def test_deliverable_is_one_coherent_document(self) -> None:
        orch = self.orchestrator(ScriptedProvider())
        record = orch.run(COMPLEX)
        doc = orch.deliverable(record)
        self.assertIn(f"# OmniBrain run {record.run_id}", doc)
        self.assertIn("**Verdict:**", doc)
        self.assertIn("## Deliverables", doc)
        self.assertIn("## Gates", doc)
        for result in record.by_task().values():
            self.assertIn(result.agent_id, doc)


if __name__ == "__main__":
    unittest.main()
