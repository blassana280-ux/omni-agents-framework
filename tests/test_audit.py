"""Offline tests of the account audit logic (the live audit is a CLI command)."""

from __future__ import annotations

import unittest

from omni.audit import INJECTED_SIZE, analyse_inventory, classify_agents_md


def row(name, size, sha, upstream, parent="owner/repo", branch="main"):
    return {
        "name": name,
        "branch": branch,
        "agents_md_size": size,
        "agents_md_sha": sha,
        "upstream_agents_md_size": upstream,
        "parent": parent,
    }


class TestAuditAnalysis(unittest.TestCase):
    def test_classification(self) -> None:
        self.assertEqual(classify_agents_md(INJECTED_SIZE, "3116c8cadc"), "injected")
        self.assertEqual(classify_agents_md(1682, "deadbeef00"), "custom")
        self.assertEqual(classify_agents_md(None, None), "absent")
        self.assertEqual(classify_agents_md(1960, "8442d59ebf"), "custom")

    def test_overwrite_detected_only_when_upstream_had_the_file(self) -> None:
        reports = analyse_inventory(
            [
                row("agentskills", INJECTED_SIZE, "3116c8cadc", 1960),
                row("copied-fork", INJECTED_SIZE, "3116c8cadc", None),
                row("untouched", 1960, "8442d59ebf", 1960),
                row("no-parent", INJECTED_SIZE, "3116c8cadc", None, parent="-"),
            ]
        )
        by_name = {r.name: r for r in reports}
        self.assertTrue(by_name["agentskills"].overwritten)
        self.assertFalse(by_name["copied-fork"].overwritten)
        self.assertEqual(by_name["copied-fork"].upstream_agents_md, "absent")
        self.assertFalse(by_name["untouched"].overwritten)
        self.assertEqual(by_name["untouched"].agents_md, "custom")
        self.assertEqual(by_name["no-parent"].upstream_agents_md, "unknown")
        self.assertIn("no instruction lost", " ".join(by_name["copied-fork"].notes))


if __name__ == "__main__":
    unittest.main()
