"""Regression tests for secret redaction at persistence boundaries."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from tests.helpers import load_registry
from omni.memory import redact
from omni.messaging import Message, MessageBus
from omni.models import Assignment, Brief, Classification, Plan, Result, RunRecord, Task
from omni.orchestrator import Orchestrator
from omni.trace import Trace
from omni.validation import ValidationEngine


class PersistenceRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = load_registry(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_plan_record(self, **result_fields):
        task = Task(
            id="task-1",
            specialty="backend",
            title="Test task",
            objective="Test persistence redaction",
            acceptance_criteria=[],
        )
        brief = Brief(
            task_id=task.id,
            agent_id="omni-backend",
            specialty=task.specialty,
            objective=task.objective,
            acceptance_criteria=[],
            allowed_tools=[],
            boundaries=[],
        )
        plan = Plan(
            request="safe request",
            classification=Classification(
                size="simple",
                scores={},
                specialties=["backend"],
                rationale="test",
            ),
            tasks=[task],
            assignments=[Assignment(task, "omni-backend", 1, brief)],
            squad=["omni-backend"],
        )
        fields = {
            "task_id": task.id,
            "agent_id": "omni-backend",
            "status": "ok",
            "summary": "completed",
            "evidence": ["test evidence"],
            "artifacts": [],
            "met_criteria": [],
            "claims": {},
            "executed": True,
            "provider": "test-provider",
        }
        fields.update(result_fields)
        record = RunRecord(request="safe request", results=[Result(**fields)])
        trace = Trace(record.run_id)
        trace.emit("dispatch", task=task.id, agent="omni-backend")
        trace.emit("result", task=task.id, agent="omni-backend", status="ok")
        return plan, record, trace

    def test_message_bus_redacts_subject_body_payload_and_mapping_keys(self) -> None:
        path = self.root / "bus.jsonl"
        bus = MessageBus(path, "run-1", {"omnibrain", "omni-qa"})
        secrets = [
            "api_key=super-secret-value",
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234",
            "sk-proj-abcdefghijklmnop12345",
            "AKIAABCDEFGHIJKLMNOP",
        ]
        message = Message(
            run_id="run-1",
            sender="omnibrain",
            recipient="omni-qa",
            subject=secrets[0],
            body=secrets[1],
            payload={
                secrets[2]: secrets[3],
                "nested": {"token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"},
            },
        )

        sent = bus.send(message)
        stored = path.read_text(encoding="utf-8")
        self.assertIs(sent, message)
        for secret in secrets:
            self.assertNotIn(secret, stored)
        self.assertEqual(bus.inbox("omni-qa")[0]["subject"], "[REDACTED]")
        self.assertEqual(message.body, "[REDACTED]")

    def test_message_bus_redacts_legacy_data_when_read(self) -> None:
        path = self.root / "legacy-bus.jsonl"
        path.write_text(
            json.dumps({
                "run_id": "run-legacy",
                "sender": "omnibrain",
                "recipient": "omni-qa",
                "subject": "safe",
                "body": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234",
                "kind": "info",
                "payload": None,
            }) + "\n",
            encoding="utf-8",
        )
        bus = MessageBus(path, "run-legacy", {"omnibrain", "omni-qa"})
        self.assertEqual(bus.all()[0]["body"], "[REDACTED]")

    def test_trace_redacts_fields_before_memory_and_disk(self) -> None:
        path = self.root / "run.jsonl"
        trace = Trace("run-trace", path)
        secret = "sk-proj-abcdefghijklmnop12345"
        event = trace.emit(
            "provider_result",
            summary=secret,
            nested={"api_key": "api_key=super-secret-value"},
        )

        stored = path.read_text(encoding="utf-8")
        self.assertNotIn(secret, stored)
        self.assertNotIn(secret, json.dumps(trace.events))
        self.assertEqual(event["summary"], "[REDACTED]")
        self.assertEqual(event["nested"]["api_key"], "[REDACTED]")

    def test_validation_gate_checks_all_result_surfaces(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        surfaces = {
            "request": lambda record: setattr(record, "request", secret),
            "summary": lambda record: setattr(record.results[0], "summary", secret),
            "evidence": lambda record: setattr(record.results[0], "evidence", [secret]),
            "artifacts": lambda record: setattr(record.results[0], "artifacts", [secret]),
            "claims": lambda record: setattr(record.results[0], "claims", {"credential": secret}),
            "error": lambda record: setattr(record.results[0], "error", secret),
        }
        for name, inject in surfaces.items():
            with self.subTest(surface=name):
                plan, record, trace = self.make_plan_record()
                inject(record)
                findings = ValidationEngine().check(record, plan, trace)
                secrets_gate = next(f for f in findings if f.gate == "secrets")
                self.assertFalse(secrets_gate.passed, name)

    def test_run_snapshot_is_redacted_and_private(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        _, record, _ = self.make_plan_record(
            evidence=[secret],
            claims={"secret": secret},
        )
        record.request = "request included token " + secret
        orchestrator = Orchestrator(
            self.registry,
            workspace=self.root,
            state_dir=self.root / ".omni",
        )
        orchestrator._persist(record)

        run_file = self.root / ".omni" / "runs" / f"{record.run_id}.json"
        contents = run_file.read_text(encoding="utf-8")
        self.assertNotIn(secret, contents)
        persisted = json.loads(contents)
        self.assertEqual(persisted["results"][0]["evidence"], ["[REDACTED]"])
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(run_file.stat().st_mode), 0o600)

    @unittest.skipIf(os.name == "nt", "POSIX file permission mode is not available on Windows")
    def test_message_and_trace_files_are_private(self) -> None:
        bus_path = self.root / "bus-private.jsonl"
        trace_path = self.root / "trace-private.jsonl"
        MessageBus(bus_path, "run-1", {"omnibrain"})
        Trace("run-1", trace_path)
        self.assertEqual(stat.S_IMODE(bus_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(trace_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
