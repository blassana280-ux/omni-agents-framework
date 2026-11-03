"""Evidence Engine : chaîne de hachage, altération détectée."""

from __future__ import annotations

import json


def test_chain_verifies_when_intact(evidence):
    evidence.record("task_start", agent="CI-001")
    evidence.record("task_done", agent="CI-001")
    verdict = evidence.verify()
    assert verdict["ok"] is True
    assert verdict["entries"] == 2


def test_tampering_detected(evidence, tmp_path):
    evidence.record("task_start", agent="CI-001")
    evidence.record("task_done", agent="CI-001")
    # falsification manuelle du journal
    lines = evidence.path.read_text(encoding="utf-8").strip().split("\n")
    entry = json.loads(lines[0])
    entry["kind"] = "task_done"  # réécriture interdite
    lines[0] = json.dumps(entry, ensure_ascii=False)
    evidence.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    verdict = EvidenceEngine(evidence.path).verify()
    assert verdict["ok"] is False
    assert "broken_at" in verdict


def test_entry_removed_detected(evidence):
    evidence.record("a", agent="x")
    evidence.record("b", agent="x")
    evidence.record("c", agent="x")
    lines = evidence.path.read_text(encoding="utf-8").strip().split("\n")
    evidence.path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    verdict = EvidenceEngine(evidence.path).verify()
    assert verdict["ok"] is False


def test_evidence_order_and_prev_hash(evidence):
    e1 = evidence.record("first", agent="AI")
    e2 = evidence.record("second", agent="AI")
    assert e1["prev_hash"] == "0" * 64
    assert e2["prev_hash"] == e1["hash"]
