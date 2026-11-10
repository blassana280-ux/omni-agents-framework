"""Permissions, controlled memory and the agent message bus."""

from __future__ import annotations

import json
import multiprocessing
import os
import stat
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests.helpers import load_registry
from omni.memory import MemoryCorruptionError, MemoryDenied, SharedMemory, redact
from omni.messaging import Message, MessageBus, UnknownAgent
from omni.policy import Policy, PolicyDenied


def _memory_process_writer(path: str, worker: int, writes: int) -> None:
    """Top-level target so the test also works with multiprocessing spawn."""
    memory = SharedMemory(path, f"process-{worker}", writable_shared=["omnibrain"])
    for index in range(writes):
        memory.write(
            "shared",
            f"process-{worker}-{index}",
            {"worker": worker, "index": index},
            owner="omnibrain",
        )


class TestPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = load_registry(Path(self.tmp.name))
        self.policy = Policy(self.registry.permissions)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_granted_tool_is_allowed(self) -> None:
        self.assertTrue(self.policy.check("omni-qa", "run_tests").allowed)
        self.assertIn("execute_task", self.policy.allowed_tools("omni-qa"))

    def test_ungranted_tool_is_denied(self) -> None:
        decision = self.policy.check("omni-designer", "git_push")
        self.assertFalse(decision.allowed)
        self.assertIn("not granted", decision.reason)
        with self.assertRaises(PolicyDenied):
            self.policy.require("omni-designer", "git_push")

    def test_unknown_agent_is_denied(self) -> None:
        self.assertFalse(self.policy.check("omni-ghost", "read_file").allowed)

    def test_reviewer_cannot_push(self) -> None:
        # an independent reviewer must not be able to publish its own findings
        self.assertFalse(self.policy.check("omni-reviewer", "git_push").allowed)

    def test_dangerous_action_requires_confirmation(self) -> None:
        decision = self.policy.check("omni-gitops", "merge_pr")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_confirmation)
        self.assertFalse(self.policy.check("omni-gitops", "merge_pr", confirmed=True).allowed)

    def test_path_rule_denies_secrets(self) -> None:
        decision = self.policy.check("omni-backend", "write_file", resource=".env")
        self.assertFalse(decision.allowed)


class TestSharedMemory(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "memory.json"
        self.memory = SharedMemory(self.path, "run-1", writable_shared=["omnibrain"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_own_namespace_write_and_read(self) -> None:
        self.memory.write("run", "note", {"a": 1}, owner="omni-backend")
        self.assertEqual(self.memory.get("run", "note"), {"a": 1})

    def test_shared_write_requires_grant(self) -> None:
        with self.assertRaises(MemoryDenied):
            self.memory.write("shared", "plan", {"x": 1}, owner="omni-backend")
        self.memory.write("shared", "plan", {"x": 1}, owner="omnibrain")
        self.assertEqual(self.memory.get("shared", "plan"), {"x": 1})

    def test_secrets_are_redacted_before_persisting(self) -> None:
        raw = {
            "token": "ghp_abcdefghijklmnopqrstuvwx1234",
            "key": "sk-proj-abcdefghijklmnop12345",
            "aws": "AKIAABCDEFGHIJKLMNOP",
            "note": "api_key=super-secret-value",
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ": "secret in a mapping key",
        }
        self.memory.write("run", "leak", raw, owner="omni-backend")
        stored = self.path.read_text(encoding="utf-8")
        for secret in (
            "ghp_abcdefghijklmnopqrstuvwx1234",
            "sk-proj-abcdefghijklmnop12345",
            "AKIAABCDEFGHIJKLMNOP",
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ):
            self.assertNotIn(secret, stored)
        self.assertEqual(redact("sk-proj-abcdefghijklmnop12345"), "[REDACTED]")

    def test_ttl_expiry(self) -> None:
        self.memory.write("run", "short", "value", owner="omni-qa", ttl_s=1)
        self.assertEqual(self.memory.get("run", "short"), "value")
        time.sleep(1.1)
        self.assertIsNone(self.memory.get("run", "short"))
        self.assertEqual(self.memory.purge_expired(), 1)
        self.memory.write("run", "long", "value", owner="omni-qa", ttl_s=60)
        time.sleep(1.1)
        self.assertEqual(self.memory.purge_expired(), 0)
        self.assertEqual(self.memory.get("run", "long"), "value")

    def test_search_finds_value(self) -> None:
        self.memory.write("run", "k", {"finding": "n+1 query on /users"}, owner="omni-debugger")
        hits = self.memory.search("n+1")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["owner"], "omni-debugger")

    def test_concurrent_thread_writes_are_not_lost(self) -> None:
        def write_batch(worker: int) -> None:
            memory = SharedMemory(
                self.path,
                f"thread-{worker}",
                writable_shared=["omnibrain"],
            )
            for index in range(12):
                memory.write(
                    "shared",
                    f"thread-{worker}-{index}",
                    {"worker": worker, "index": index},
                    owner="omnibrain",
                )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(write_batch, range(8)))

        entries = json.loads(self.path.read_text(encoding="utf-8"))["entries"]
        self.assertEqual(len(entries), 8 * 12)

    def test_concurrent_process_writes_are_not_lost(self) -> None:
        context = multiprocessing.get_context("spawn")
        processes = [
            context.Process(target=_memory_process_writer, args=(str(self.path), worker, 5))
            for worker in range(3)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)

        still_running = [process for process in processes if process.is_alive()]
        for process in still_running:
            process.terminate()
            process.join(timeout=5)
        self.assertFalse(still_running, "memory writer process deadlocked")
        self.assertEqual([process.exitcode for process in processes], [0, 0, 0])

        entries = json.loads(self.path.read_text(encoding="utf-8"))["entries"]
        self.assertEqual(len(entries), 3 * 5)

    def test_corrupt_store_fails_closed_without_overwrite(self) -> None:
        self.path.write_text('{"entries": ', encoding="utf-8")
        original = self.path.read_text(encoding="utf-8")

        with self.assertRaises(MemoryCorruptionError):
            self.memory.write("shared", "plan", {"x": 1}, owner="omnibrain")

        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_invalid_ttl_is_rejected(self) -> None:
        for ttl in (0, -1, True):
            with self.subTest(ttl=ttl):
                with self.assertRaises(ValueError):
                    self.memory.write("run", "bad-ttl", "value", owner="omni-qa", ttl_s=ttl)

    def test_memory_addresses_cannot_contain_credentials(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.write("run", "api_key=super-secret-value", "value", owner="omni-qa")

    @unittest.skipIf(os.name == "nt", "POSIX file permission mode is not available on Windows")
    def test_memory_and_lock_files_are_private(self) -> None:
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)


class TestMessageBus(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "bus.jsonl"
        self.bus = MessageBus(self.path, "run-1", {"omnibrain", "omni-qa", "omni-reviewer"})

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_roundtrip(self) -> None:
        self.bus.send(Message(run_id="run-1", sender="omnibrain", recipient="omni-qa",
                              subject="run the suite", body="please"))
        inbox = self.bus.inbox("omni-qa")
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["subject"], "run the suite")
        self.assertEqual(self.bus.outbox("omnibrain")[0]["recipient"], "omni-qa")

    def test_unknown_agent_is_rejected(self) -> None:
        with self.assertRaises(UnknownAgent):
            self.bus.send(Message(run_id="run-1", sender="omnibrain", recipient="omni-ghost",
                                  subject="s", body="b"))
        with self.assertRaises(UnknownAgent):
            self.bus.send(Message(run_id="run-1", sender="omni-ghost", recipient="omni-qa",
                                  subject="s", body="b"))

    def test_other_runs_are_isolated(self) -> None:
        other = MessageBus(self.path, "run-2", {"omnibrain", "omni-qa"})
        other.send(Message(run_id="run-2", sender="omnibrain", recipient="omni-qa", subject="s", body="b"))
        self.assertEqual(self.bus.all(), [])
        self.assertEqual(len(other.all()), 1)


if __name__ == "__main__":
    unittest.main()
