"""The OmniBrain orchestrator.

Flow: classify -> plan -> parallel waves -> failure handling -> correction loop
-> arbitration -> validation gates -> single verdict + trace.

Threads are real: a wave is executed with :class:`ThreadPoolExecutor`, and the
measured wall time is recorded so parallelism is observable, not claimed.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .executor import ManualProvider, Provider
from .memory import SharedMemory
from .messaging import Message, MessageBus
from .models import (
    Arbitration,
    Assignment,
    Brief,
    Classification,
    Correction,
    Plan,
    ProviderResult,
    Result,
    RunRecord,
    Task,
)
from .policy import Policy
from .registry import Registry
from .routing import Router
from .trace import Trace
from .validation import ValidationEngine, verdict_for

OMNIBRAIN = "omnibrain"


class Orchestrator:
    def __init__(
        self,
        registry: Registry,
        provider: Optional[Provider] = None,
        *,
        workspace: str | Path = ".",
        state_dir: Optional[str | Path] = None,
        max_parallel: int = 4,
        retries: int = 1,
        correction_rounds: int = 1,
        require_execution: bool = True,
    ) -> None:
        self.registry = registry
        self.provider = provider or ManualProvider()
        self.policy = Policy(registry.permissions)
        self.router = Router(registry, self.policy)
        self.workspace = Path(workspace)
        self.state_dir = Path(state_dir or self.workspace / ".omni")
        self.max_parallel = max_parallel
        self.retries = retries
        self.correction_rounds = correction_rounds
        self.validator = ValidationEngine(require_execution=require_execution)

    # ------------------------------------------------------------------ plan
    def plan(self, request: str) -> Plan:
        return self.router.plan(request)

    def classify(self, request: str) -> Classification:
        return self.router.classify(request)

    # ------------------------------------------------------------------- run
    def run(self, request: str, plan: Optional[Plan] = None) -> RunRecord:
        record = RunRecord(request=request)
        plan = plan or self.plan(request)
        trace = Trace(record.run_id, self.state_dir / "runs" / f"{record.run_id}.jsonl")
        memory = SharedMemory(self.state_dir / "memory.json", record.run_id, writable_shared=[OMNIBRAIN])
        bus = MessageBus(self.state_dir / "bus.jsonl", record.run_id, set(self.registry.agents) | {OMNIBRAIN})

        record.size = plan.classification.size
        record.specialties = list(plan.classification.specialties)
        record.squad = list(plan.squad)
        record.unresolved_specialties = list(plan.unresolved_specialties)
        trace.emit(
            "plan",
            size=record.size,
            specialties=record.specialties,
            squad=record.squad,
            rationale=plan.classification.rationale,
            waves=len(plan.waves),
            unresolved=record.unresolved_specialties,
        )
        for sid in plan.unresolved_specialties:
            trace.emit("missing_specialty", specialty=sid)

        # ---------------------------------------------------------- waves
        for index, wave in enumerate(plan.waves, start=1):
            started = time.time()
            results = self._run_wave(wave, trace)
            wall = round(time.time() - started, 4)
            record.results.extend(results)
            trace.emit(
                "wave",
                wave=index,
                size=len(wave),
                wall_s=wall,
                serial_s=round(sum(r.duration_s for r in results), 4),
                tasks=[r.task_id for r in results],
                executed=[r.executed for r in results],
            )
            self._handle_failures(wave, results, record, trace, bus, memory)

        # ---------------------------------------------------- corrections
        self._correction_loop(plan, record, trace, bus, memory)

        # ---------------------------------------------------- arbitration
        record.arbitrations = self._arbitrate(record, trace)

        # --------------------------------------------------------- gates
        record.findings = self.validator.check(record, plan, trace)
        record.verdict = verdict_for(record.findings)
        record.finished_at = time.time()

        trace.emit(
            "verdict",
            verdict=record.verdict,
            failed_gates=[f.gate for f in record.findings if not f.passed],
        )
        record.trace = trace.events

        memory.write(
            "shared",
            f"verdict:{record.run_id}",
            {
                "request": request,
                "verdict": record.verdict,
                "squad": record.squad,
                "failed_gates": [f.gate for f in record.findings if not f.passed],
            },
            owner=OMNIBRAIN,
        )
        self._persist(record)
        return record

    # -------------------------------------------------------------- internals
    def _run_wave(self, wave: Sequence[Assignment], trace: Trace) -> List[Result]:
        workers = max(1, min(self.max_parallel, len(wave)))
        if workers == 1:
            return [self._dispatch(a, trace) for a in wave]
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="omni") as pool:
            futures = [pool.submit(self._dispatch, a, trace) for a in wave]
            return [f.result() for f in futures]

    def _dispatch(
        self,
        assignment: Assignment,
        trace: Trace,
        *,
        attempt: int = 1,
        agent_id: Optional[str] = None,
        missing: Optional[List[str]] = None,
        reassigned_from: Optional[str] = None,
    ) -> Result:
        agent_id = agent_id or assignment.agent_id
        agent = self.registry.agents[agent_id]
        task = assignment.task
        brief = Brief(
            task_id=task.id,
            agent_id=agent_id,
            specialty=task.specialty,
            objective=task.objective,
            acceptance_criteria=task.acceptance_criteria,
            allowed_tools=self.policy.allowed_tools(agent_id),
            boundaries=agent.boundaries,
            context={"request": assignment.brief.context.get("request", ""), "specialty": task.specialty},
            attempt=attempt,
            correction_of=task.id if missing else None,
            missing_criteria=list(missing or []),
        )

        decision = self.policy.check(agent_id, "execute_task")
        trace.emit(
            "policy",
            agent=agent_id,
            action="execute_task",
            allowed=decision.allowed,
            reason=decision.reason,
        )
        trace.emit(
            "dispatch",
            task=task.id,
            agent=agent_id,
            specialty=task.specialty,
            attempt=attempt,
            wave=assignment.wave,
            tools=brief.allowed_tools,
            provider=getattr(self.provider, "name", "unknown"),
        )
        if not decision.allowed:
            result = Result(
                task_id=task.id,
                agent_id=agent_id,
                status="failed",
                summary="",
                evidence=[],
                artifacts=[],
                met_criteria=[],
                claims={},
                executed=False,
                provider="none",
                attempt=attempt,
                error=decision.reason,
                reassigned_from=reassigned_from,
            )
            trace.emit("result", task=task.id, agent=agent_id, status="failed", executed=False, error=decision.reason)
            return result

        started = time.time()
        try:
            provider_result = self.provider.execute(brief, self.workspace)
        except Exception as exc:  # a provider crash must not kill the run
            provider_result = ProviderResult(
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                provider=getattr(self.provider, "name", "unknown"),
                executed=False,
                duration_s=time.time() - started,
            )

        result = Result.from_provider(brief, provider_result, reassigned_from=reassigned_from)
        # measure it ourselves: a provider's self-reported duration is not evidence
        result.duration_s = round(time.time() - started, 4)
        trace.emit(
            "result",
            task=task.id,
            agent=agent_id,
            status=result.status,
            executed=result.executed,
            provider=result.provider,
            evidence=len(result.evidence),
            met=result.met_criteria,
        )
        return result

    def _handle_failures(
        self,
        wave: Sequence[Assignment],
        results: List[Result],
        record: RunRecord,
        trace: Trace,
        bus: MessageBus,
        memory: SharedMemory,
    ) -> None:
        by_task = {a.task.id: a for a in wave}
        for result in list(results):
            if result.status not in ("failed",):
                continue
            assignment = by_task[result.task_id]

            # 1. retry with the same agent
            for attempt in range(2, self.retries + 2):
                trace.emit("retry", task=result.task_id, agent=result.agent_id, attempt=attempt)
                retried = self._dispatch(assignment, trace, attempt=attempt)
                record.results.append(retried)
                result = retried
                if retried.status != "failed":
                    break
            if result.status != "failed":
                continue

            # 2. reassign to a fallback agent for that specialty
            fallbacks = self.registry.fallbacks(assignment.task.specialty, exclude=[result.agent_id])
            if fallbacks:
                fallback = fallbacks[0]
                trace.emit(
                    "reassign",
                    task=result.task_id,
                    from_agent=result.agent_id,
                    to_agent=fallback,
                    specialty=assignment.task.specialty,
                )
                bus.send(
                    Message(
                        run_id=record.run_id,
                        sender=OMNIBRAIN,
                        recipient=fallback,
                        subject=f"takeover {result.task_id}",
                        body=f"Agent {result.agent_id} failed on {assignment.task.title}: {result.error or result.status}",
                        kind="correction",
                        payload={"task": result.task_id, "missing": []},
                    )
                )
                reassigned = self._dispatch(
                    assignment,
                    trace,
                    agent_id=fallback,
                    attempt=result.attempt + 1,
                    reassigned_from=result.agent_id,
                )
                record.results.append(reassigned)
                if reassigned.status != "failed":
                    memory.write(
                        "shared",
                        f"reassign:{result.task_id}",
                        {"from": result.agent_id, "to": fallback, "status": reassigned.status},
                        owner=OMNIBRAIN,
                    )
                    continue
                result = reassigned

            # 3. escalate: no fallback worked
            trace.emit("escalate", task=result.task_id, agent=result.agent_id, reason="no fallback agent succeeded")
            bus.send(
                Message(
                    run_id=record.run_id,
                    sender=OMNIBRAIN,
                    recipient=record.squad[0] if record.squad else list(self.registry.agents)[0],
                    subject=f"escalation {result.task_id}",
                    body="All agents and fallbacks failed; human arbitration required.",
                    kind="question",
                )
            )

    def _correction_loop(
        self,
        plan: Plan,
        record: RunRecord,
        trace: Trace,
        bus: MessageBus,
        memory: SharedMemory,
    ) -> None:
        for round_no in range(1, self.correction_rounds + 1):
            latest = record.by_task()
            pending: List[tuple[Task, Assignment, List[str]]] = []
            for assignment in plan.assignments:
                task = assignment.task
                result = latest.get(task.id)
                if result is None or result.status == "failed":
                    continue
                unmet = [c for c in task.acceptance_criteria if c not in result.met_criteria]
                if result.status != "ok" or unmet:
                    pending.append((task, assignment, unmet))
            if not pending:
                return
            for task, assignment, unmet in pending:
                agent_id = latest[task.id].agent_id
                record.corrections.append(
                    Correction(task_id=task.id, agent_id=agent_id, missing_criteria=unmet, round=round_no)
                )
                trace.emit("correction_request", task=task.id, agent=agent_id, missing=unmet, round=round_no)
                bus.send(
                    Message(
                        run_id=record.run_id,
                        sender=OMNIBRAIN,
                        recipient=agent_id,
                        subject=f"correction {task.id} round {round_no}",
                        body="Deliverable incomplete. Missing: " + (", ".join(unmet) or "no acceptance criteria met"),
                        kind="correction",
                        payload={"missing": unmet, "round": round_no},
                    )
                )
                corrected = self._dispatch(
                    assignment,
                    trace,
                    attempt=latest[task.id].attempt + 1,
                    agent_id=agent_id,
                    missing=unmet,
                )
                record.results.append(corrected)
                memory.write(
                    "run",
                    f"correction:{task.id}:r{round_no}",
                    {"agent": agent_id, "missing": unmet, "status": corrected.status},
                    owner=OMNIBRAIN,
                )

    # ---------------------------------------------------------- arbitration
    def _arbitrate(self, record: RunRecord, trace: Trace) -> List[Arbitration]:
        latest = record.by_task()
        topics: Dict[str, Dict[str, Any]] = {}
        for result in latest.values():
            for topic, value in result.claims.items():
                topics.setdefault(topic, {})[result.task_id] = value

        arbitrations: List[Arbitration] = []
        for topic, per_task in topics.items():
            distinct = {json.dumps(v, sort_keys=True, default=str) for v in per_task.values()}
            if len(distinct) <= 1:
                continue
            ranked = sorted(
                per_task.items(),
                key=lambda kv: (
                    -len(latest[kv[0]].evidence),
                    not latest[kv[0]].executed,
                    -len(latest[kv[0]].met_criteria),
                    kv[0],
                ),
            )
            (win_task, _), (run_task, _) = ranked[0], ranked[1]
            w = latest[win_task]
            r = latest[run_task]
            tie = (
                len(w.evidence) == len(r.evidence)
                and w.executed == r.executed
                and len(w.met_criteria) == len(r.met_criteria)
            )
            arbitration = Arbitration(
                topic=topic,
                values=per_task,
                winner_agent=w.agent_id,
                winner_task=win_task,
                rule="evidence_count > execution > criteria_met > task_id" if not tie else "unresolved tie",
                resolved=not tie,
            )
            arbitrations.append(arbitration)
            trace.emit(
                "arbitration",
                topic=topic,
                winner=w.agent_id,
                winner_task=win_task,
                resolved=arbitration.resolved,
                rule=arbitration.rule,
                values=per_task,
            )
        return arbitrations

    # ------------------------------------------------------------ persistence
    def _persist(self, record: RunRecord) -> None:
        out = self.state_dir / "runs" / f"{record.run_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def deliverable(self, record: RunRecord) -> str:
        """Assemble one coherent document from all results."""
        lines = [
            f"# OmniBrain run {record.run_id}",
            "",
            f"**Request:** {record.request}",
            f"**Classification:** {record.size} — {', '.join(record.specialties)}",
            f"**Squad:** {', '.join(record.squad) or '(none)'}",
            f"**Verdict:** {record.verdict}",
            "",
        ]
        if record.unresolved_specialties:
            lines += [f"**Unstaffed specialties:** {', '.join(record.unresolved_specialties)}", ""]
        lines.append("## Deliverables")
        latest = record.by_task()
        for task_id in latest:
            r = latest[task_id]
            lines += [
                f"### {task_id} — {r.agent_id}",
                f"- status: `{r.status}` (executed by provider: {r.executed}, `{r.provider}`)",
                r.summary or "_(no summary)_",
            ]
            if r.error:
                lines.append(f"- error: {r.error}")
            if r.evidence:
                lines.append("- evidence: " + "; ".join(r.evidence))
            if r.artifacts:
                lines.append("- artifacts: " + ", ".join(r.artifacts))
            lines.append("")
        if record.corrections:
            lines.append("## Corrections requested")
            lines += [
                f"- {c.task_id} → {c.agent_id} (round {c.round}): missing {c.missing_criteria or 'criteria'}"
                for c in record.corrections
            ]
            lines.append("")
        if record.arbitrations:
            lines.append("## Arbitrations")
            lines += [
                f"- {a.topic}: kept `{a.winner_agent}` ({a.rule}); resolved={a.resolved}"
                for a in record.arbitrations
            ]
            lines.append("")
        lines.append("## Gates")
        lines += [f"- {f.gate}: {'PASS' if f.passed else 'FAIL'} — {f.detail}" for f in record.findings]
        return "\n".join(lines)
