"""Regression tests for secret redaction at persistence boundaries."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tests.helpers import load_registry
from omni.memory import MemoryStorageError, SharedMemory, redact
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

    def test_message_bus_rejects_unrecognized_kinds(self) -> None:
        bus = MessageBus(self.root / "invalid-kind.jsonl", "run-1", {"omnibrain", "omni-qa"})
        message = Message(
            run_id="run-1",
            sender="omnibrain",
            recipient="omni-qa",
            subject="subject",
            body="body",
            kind="not-a-supported-kind",
        )
        with self.assertRaises(ValueError):
            bus.send(message)
        self.assertEqual(bus.all(), [])

    def test_message_bus_rejects_cross_run_messages_without_persisting(self) -> None:
        path = self.root / "cross-run.jsonl"
        bus = MessageBus(path, "run-1", {"omnibrain", "omni-qa"})
        message = Message(
            run_id="run-2",
            sender="omnibrain",
            recipient="omni-qa",
            subject="wrong run",
            body="must not be stored",
        )
        with self.assertRaises(ValueError):
            bus.send(message)
        self.assertEqual(path.read_text(encoding="utf-8"), "")

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

    def test_trace_redacts_custom_stringified_values(self) -> None:
        class SecretValue:
            def __str__(self) -> str:
                return "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"

        path = self.root / "custom-value.jsonl"
        trace = Trace("run-custom-value", path)
        event = trace.emit("custom_value", payload=SecretValue())

        stored = path.read_text(encoding="utf-8")
        self.assertEqual(event["payload"], "[REDACTED]")
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234", stored)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234", json.dumps(trace.events))

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

    def test_user_deliverable_redacts_secrets_from_request_and_results(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        record = RunRecord(
            request=f"Deploy with token {secret}",
            results=[
                Result(
                    task_id="task-1",
                    agent_id="omni-backend",
                    status="ok",
                    summary=f"Used credential {secret}",
                    evidence=[secret],
                    artifacts=[],
                    met_criteria=[],
                    claims={},
                    executed=True,
                    provider="test-provider",
                )
            ],
        )
        document = Orchestrator(self.registry, workspace=self.root).deliverable(record)
        self.assertNotIn(secret, document)
        self.assertIn("[REDACTED]", document)

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



    def test_run_identifiers_cannot_contain_credentials(self) -> None:
        secret_run_id = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        with self.assertRaises(ValueError):
            MessageBus(self.root / "secret-run.jsonl", secret_run_id, {"omnibrain"})
        with self.assertRaises(ValueError):
            Trace(secret_run_id, self.root / "secret-trace.jsonl")
        self.assertFalse((self.root / "secret-run.jsonl").exists())
        self.assertFalse((self.root / "secret-trace.jsonl").exists())


    def test_tuple_values_are_redacted_before_json_persistence(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"

        memory_path = self.root / "tuple-memory.json"
        memory = SharedMemory(memory_path, "run-tuple")
        memory.write("run", "nested", {"items": (secret,)}, owner="omni-backend")
        stored_memory = memory_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, stored_memory)
        self.assertEqual(
            json.loads(stored_memory)["entries"]["run::run-tuple::nested"]["value"]["items"],
            ["[REDACTED]"],
        )

        bus_path = self.root / "tuple-bus.jsonl"
        bus = MessageBus(bus_path, "run-tuple", {"omnibrain", "omni-qa"})
        bus.send(Message(
            run_id="run-tuple",
            sender="omnibrain",
            recipient="omni-qa",
            subject="tuple test",
            body="nested tuple",
            payload={"items": (secret,)},
        ))
        self.assertNotIn(secret, bus_path.read_text(encoding="utf-8"))

        trace_path = self.root / "tuple-trace.jsonl"
        trace = Trace("run-tuple", trace_path)
        trace.emit("tuple_test", items=(secret,))
        self.assertNotIn(secret, trace_path.read_text(encoding="utf-8"))


    def test_run_scope_isolated_between_shared_memory_instances(self) -> None:
        path = self.root / "shared-memory-runs.json"
        first = SharedMemory(path, "run-one", writable_shared=["omnibrain"])
        second = SharedMemory(path, "run-two", writable_shared=["omnibrain"])

        first.write("run", "private", {"marker": "first-run-only"}, owner="omni-backend")
        self.assertIsNone(second.get("run", "private"))
        self.assertEqual(second.search("first-run-only"), [])
        self.assertEqual(second.search("first-run-only", scope="run"), [])

        second.write("run", "private", {"marker": "second-run-only"}, owner="omni-backend")
        self.assertEqual(first.get("run", "private"), {"marker": "first-run-only"})
        self.assertEqual(second.get("run", "private"), {"marker": "second-run-only"})
        self.assertEqual(first.search("first-run-only", scope="run")[0]["run_id"], "run-one")
        self.assertEqual(second.search("second-run-only", scope="run")[0]["run_id"], "run-two")

    def test_shared_scope_remains_visible_across_runs(self) -> None:
        path = self.root / "shared-memory-global.json"
        first = SharedMemory(path, "run-one", writable_shared=["omnibrain"])
        second = SharedMemory(path, "run-two", writable_shared=["omnibrain"])

        first.write("shared", "project-context", {"marker": "shared-context"}, owner="omnibrain")
        self.assertEqual(second.get("shared", "project-context"), {"marker": "shared-context"})
        self.assertEqual(second.search("shared-context", scope="shared")[0]["run_id"], "run-one")

    def test_existing_memory_is_redacted_when_opened(self) -> None:
        secret_key = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        secret_value = "api_key=legacy-secret-value"
        path = self.root / "legacy-memory.json"
        legacy = {
            "entries": {
                "run-legacy::facts": {
                    "value": {"nested": {secret_key: (secret_value,)}},
                    "owner": "omni-qa",
                    "run_id": "run-legacy",
                    "written_at": 1700000000.0,
                    "expires_at": None,
                }
            }
        }
        path.write_text(json.dumps(legacy), encoding="utf-8")

        memory = SharedMemory(path, "run-legacy")
        stored = path.read_text(encoding="utf-8")
        self.assertEqual(json.loads(stored)["schema_version"], 2)
        self.assertNotIn(secret_key, stored)
        self.assertNotIn(secret_value, stored)
        self.assertEqual(
            memory.get("run-legacy", "facts"),
            {"nested": {"[REDACTED]": ["[REDACTED]"]}},
        )


    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_memory_rejects_symlink_if_precheck_misses_race(self) -> None:
        target = self.root / "memory-target.json"
        original = '{"entries": {}}'
        target.write_text(original, encoding="utf-8")
        link = self.root / "memory-link.json"
        link.symlink_to(target)

        with mock.patch.object(Path, "is_symlink", return_value=False):
            with self.assertRaises(MemoryStorageError):
                SharedMemory(link, "run-symlink")

        self.assertEqual(target.read_text(encoding="utf-8"), original)


    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_message_bus_rejects_symlink_if_precheck_misses_race(self) -> None:
        target = self.root / "bus-target.jsonl"
        original = "keep-target-content\\n"
        target.write_text(original, encoding="utf-8")
        link = self.root / "bus-link.jsonl"
        link.symlink_to(target)

        with mock.patch.object(Path, "is_symlink", return_value=False):
            with self.assertRaises(OSError):
                MessageBus(link, "run-symlink", {"omnibrain"})

        self.assertEqual(target.read_text(encoding="utf-8"), original)


    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_trace_rejects_symlink_if_precheck_misses_race(self) -> None:
        target = self.root / "trace-target.jsonl"
        original = "keep-target-content\\n"
        target.write_text(original, encoding="utf-8")
        link = self.root / "trace-link.jsonl"
        link.symlink_to(target)

        with mock.patch.object(Path, "is_symlink", return_value=False):
            with self.assertRaises(OSError):
                Trace("run-symlink", link)

        self.assertEqual(target.read_text(encoding="utf-8"), original)



    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_memory_refuses_symlink_replacement_during_reads(self) -> None:
        path = self.root / "replace-memory.json"
        memory = SharedMemory(path, "run-replace")
        target = self.root / "memory-read-target.json"
        original = '{"entries": {}}'
        target.write_text(original, encoding="utf-8")
        path.unlink()
        path.symlink_to(target)

        with self.assertRaises(MemoryStorageError):
            memory.get("run", "anything")

        self.assertEqual(target.read_text(encoding="utf-8"), original)


    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_message_bus_refuses_symlink_replacement_during_send(self) -> None:
        path = self.root / "replace-bus.jsonl"
        bus = MessageBus(path, "run-replace", {"omnibrain", "omni-qa"})
        target = self.root / "bus-write-target.jsonl"
        original = "keep-target-content\\n"
        target.write_text(original, encoding="utf-8")
        path.unlink()
        path.symlink_to(target)

        with self.assertRaises(OSError):
            bus.send(Message(
                run_id="run-replace",
                sender="omnibrain",
                recipient="omni-qa",
                subject="subject",
                body="body",
            ))

        self.assertEqual(target.read_text(encoding="utf-8"), original)


    @unittest.skipIf(os.name == "nt", "POSIX symlink no-follow behavior is not available on Windows")
    def test_trace_refuses_symlink_replacement_without_retaining_failed_event(self) -> None:
        path = self.root / "replace-trace.jsonl"
        trace = Trace("run-replace", path)
        target = self.root / "trace-write-target.jsonl"
        original = "keep-target-content\\n"
        target.write_text(original, encoding="utf-8")
        path.unlink()
        path.symlink_to(target)

        with self.assertRaises(OSError):
            trace.emit("must-not-be-stored")

        self.assertEqual(target.read_text(encoding="utf-8"), original)
        self.assertEqual(trace.events, [])



    def test_ambiguous_legacy_key_is_rejected_without_rewriting_file(self) -> None:
        path = self.root / "ambiguous-legacy-memory.json"
        legacy = {
            "entries": {
                "private::run-123::cache": {
                    "value": {"marker": "must-remain-untouched"},
                    "owner": "omni-qa",
                    "run_id": "run-123",
                    "written_at": 1700000000.0,
                    "expires_at": None,
                }
            }
        }
        original = json.dumps(legacy, ensure_ascii=False)
        path.write_text(original, encoding="utf-8")

        with self.assertRaises(MemoryStorageError):
            SharedMemory(path, "run-current")

        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_versioned_memory_store_preserves_keys_containing_separator(self) -> None:
        path = self.root / "versioned-memory.json"
        memory = SharedMemory(path, "run-123")
        memory.write(
            "private",
            "run-123::cache",
            {"marker": "key-with-separator"},
            owner="omni-qa",
        )

        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], 2)

        reopened = SharedMemory(path, "run-123")
        self.assertEqual(
            reopened.get("private", "run-123::cache"),
            {"marker": "key-with-separator"},
        )


    def test_unknown_memory_schema_is_rejected_without_rewriting_file(self) -> None:
        path = self.root / "future-memory-schema.json"
        original = json.dumps({"schema_version": 999, "entries": {}})
        path.write_text(original, encoding="utf-8")

        with self.assertRaises(MemoryStorageError):
            SharedMemory(path, "run-current")

        self.assertEqual(path.read_text(encoding="utf-8"), original)

if __name__ == "__main__":
    unittest.main()
