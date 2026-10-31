"""Deliverable validation gates.

A run only reaches verdict ``READY`` when every gate passes. Gates are cheap,
deterministic and inspect the recorded run — never the provider's self-report
alone.
"""

from __future__ import annotations

import json
from typing import Dict, List

from .memory import redact
from .models import GateFinding, Plan, RunRecord
from .trace import Trace

GATES = ("completeness", "evidence", "execution", "arbitration", "secrets", "trace")


class ValidationEngine:
    def __init__(self, require_execution: bool = True) -> None:
        self.require_execution = require_execution

    def check(self, record: RunRecord, plan: Plan, trace: Trace) -> List[GateFinding]:
        findings: List[GateFinding] = []
        latest = record.by_task()

        # ---- completeness -------------------------------------------------
        missing_tasks = [t.id for t in plan.tasks if t.id not in latest]
        incomplete: List[str] = []
        for task in plan.tasks:
            result = latest.get(task.id)
            if not result:
                continue
            unmet = [c for c in task.acceptance_criteria if c not in result.met_criteria]
            if result.status not in ("ok",) or unmet:
                incomplete.append(f"{task.id}: status={result.status}, unmet={unmet or 'none'}")
        findings.append(
            GateFinding(
                gate="completeness",
                passed=not missing_tasks and not incomplete,
                detail="all tasks delivered and criteria met"
                if not missing_tasks and not incomplete
                else f"missing={missing_tasks} incomplete={incomplete}",
            )
        )

        # ---- evidence -----------------------------------------------------
        no_evidence = [
            r.task_id for r in latest.values() if r.status == "ok" and not r.evidence
        ]
        findings.append(
            GateFinding(
                gate="evidence",
                passed=not no_evidence,
                detail="every successful task carries evidence"
                if not no_evidence
                else f"tasks claiming success without evidence: {no_evidence}",
            )
        )

        # ---- execution ----------------------------------------------------
        not_executed = [
            f"{r.task_id}({r.provider})" for r in latest.values() if not r.executed
        ]
        findings.append(
            GateFinding(
                gate="execution",
                passed=(not not_executed) or (not self.require_execution),
                detail="all tasks were really executed by a provider"
                if not not_executed
                else f"not executed (no provider / human hand-off): {not_executed}",
            )
        )

        # ---- arbitration --------------------------------------------------
        unresolved = [a.topic for a in record.arbitrations if not a.resolved]
        findings.append(
            GateFinding(
                gate="arbitration",
                passed=not unresolved,
                detail="no contradictory results left unresolved"
                if not unresolved
                else f"unresolved contradictions: {unresolved}",
            )
        )

        # ---- secrets ------------------------------------------------------
        blob = json.dumps(
            {"summaries": [r.summary for r in latest.values()], "artifacts": [r.artifacts for r in latest.values()]},
            ensure_ascii=False,
        )
        leaked = redact(blob) != blob
        findings.append(
            GateFinding(
                gate="secrets",
                passed=not leaked,
                detail="no credential-looking string in deliverables"
                if not leaked
                else "credential-looking string detected in deliverables",
            )
        )

        # ---- trace --------------------------------------------------------
        dispatched = {e.get("task") for e in trace.of_type("dispatch")}
        resolved = {e.get("task") for e in trace.of_type("result")}
        missing_trace = [t.id for t in plan.tasks if t.id not in dispatched or t.id not in resolved]
        findings.append(
            GateFinding(
                gate="trace",
                passed=not missing_trace,
                detail="every task has dispatch and result trace events"
                if not missing_trace
                else f"tasks missing trace events: {missing_trace}",
            )
        )
        return findings


def verdict_for(findings: List[Dict] | List[GateFinding]) -> str:
    for f in findings:
        passed = f["passed"] if isinstance(f, dict) else f.passed
        if not passed:
            return "NEEDS_WORK"
    return "READY"
