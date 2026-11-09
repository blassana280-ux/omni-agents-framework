"""Read-only CLI facade tests for catalog inspection and scanning."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from omni.skill_catalog import SkillCatalog, SkillSource, ingest_skill
from omni.skill_catalog_cli import handle_skill_command


class SkillCatalogCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "registry"
        self.root.mkdir()
        (self.root / "skill-sources.json").write_text(
            json.dumps({"schema_version": 1, "sources": []}), encoding="utf-8"
        )
        (self.root / "skills.lock.json").write_text(
            json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8"
        )
        (self.root / "skill-policy.json").write_text(
            json.dumps({
                "schema_version": 1,
                "allowed_licenses": ["MIT", "Apache-2.0"],
                "blocking_severities": ["critical"],
                "limits": {"max_files": 128, "max_bytes": 1048576},
            }), encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, terms, snapshot_dir=None):
        return SimpleNamespace(terms=terms, registry=str(self.root), snapshot_dir=snapshot_dir)

    def test_catalog_emits_stable_empty_json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = handle_skill_command(self.args(["catalog"]))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()), {"schema_version": 1, "count": 0, "skills": []})

    def test_legacy_skill_search_is_left_to_existing_handler(self):
        self.assertIsNone(handle_skill_command(self.args(["android", "testing"])))

    def test_inspect_reports_pinned_provenance_and_trust(self):
        source = {
            "source_id": "demo", "skill_id": "demo",
            "repository_url": "https://github.com/example/skills", "skill_path": "demo",
            "commit_sha": "a" * 40, "license_spdx": "MIT",
        }
        lock = {"skill_id": "demo", "source_id": "demo", "sha256": "b" * 64, "state": "discovered"}
        (self.root / "skill-sources.json").write_text(json.dumps({"schema_version": 1, "sources": [source]}), encoding="utf-8")
        (self.root / "skills.lock.json").write_text(json.dumps({"schema_version": 1, "skills": [lock]}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = handle_skill_command(self.args(["inspect", "demo"]))
        result = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["trust"]["state"], "discovered")
        self.assertEqual(result["source"]["commit_sha"], "a" * 40)

    def test_scan_is_read_only_and_reports_heuristic_findings(self):
        source = SkillSource(
            source_id="demo", skill_id="demo", repository_url="https://github.com/example/skills",
            skill_path="demo", commit_sha="a" * 40, license_spdx="MIT",
        )
        content = "---\nname: demo\ndescription: Demo skill\nlicense: MIT\n---\nrm -rf /tmp/demo\n"
        snapshot = ingest_skill(source, {"SKILL.md": content})
        source_doc = {
            "source_id": source.source_id, "skill_id": source.skill_id,
            "repository_url": source.repository_url, "skill_path": source.skill_path,
            "commit_sha": source.commit_sha, "license_spdx": source.license_spdx,
        }
        lock_doc = {"skill_id": "demo", "source_id": "demo", "sha256": snapshot.sha256, "state": "discovered"}
        (self.root / "skill-sources.json").write_text(json.dumps({"schema_version": 1, "sources": [source_doc]}), encoding="utf-8")
        (self.root / "skills.lock.json").write_text(json.dumps({"schema_version": 1, "skills": [lock_doc]}), encoding="utf-8")
        snapshot_dir = Path(self.tmp.name) / "snapshot"
        snapshot_dir.mkdir()
        (snapshot_dir / "SKILL.md").write_text(content, encoding="utf-8")
        out = io.StringIO()
        with patch("subprocess.run") as run, contextlib.redirect_stdout(out):
            code = handle_skill_command(self.args(["scan", "demo"], snapshot_dir=str(snapshot_dir)))
        self.assertEqual(code, 0)
        run.assert_not_called()
        result = json.loads(out.getvalue())
        self.assertTrue(result["blocking"])
        self.assertEqual(result["findings"][0]["rule_id"], "destructive-command")
        lock_after = json.loads((self.root / "skills.lock.json").read_text())
        self.assertEqual(lock_after["skills"][0]["state"], "discovered")

    def test_unknown_skill_returns_nonzero(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = handle_skill_command(self.args(["inspect", "missing"]))
        self.assertEqual(code, 1)
        self.assertIn("unknown skill", err.getvalue())

    def test_bundled_superpowers_tdd_snapshot_is_pinned_and_scannable(self):
        registry = Path(__file__).resolve().parents[1] / "registry"
        catalog = SkillCatalog.load(registry)
        skill_id = "superpowers-test-driven-development"
        entry = catalog.get(skill_id)
        self.assertIsNotNone(entry)
        source, trust = entry
        self.assertEqual(source.repository_url, "https://github.com/obra/superpowers")
        self.assertEqual(source.skill_path, "skills/test-driven-development")
        self.assertEqual(source.commit_sha, "df2e996a174f49f05aa5d5777ca56fbb0aa972ec")
        self.assertEqual(source.license_spdx, "MIT")
        self.assertEqual(trust.state, "pinned")

        args = SimpleNamespace(terms=["scan", skill_id], registry=None, snapshot_dir=None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = handle_skill_command(args)
        self.assertEqual(code, 0)
        report = json.loads(out.getvalue())
        self.assertFalse(report["blocking"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sha256"], trust.sha256)

    def test_bundled_superpowers_verification_snapshot_is_pinned_and_scannable(self):
        registry = Path(__file__).resolve().parents[1] / "registry"
        catalog = SkillCatalog.load(registry)
        skill_id = "superpowers-verification-before-completion"
        entry = catalog.get(skill_id)
        self.assertIsNotNone(entry)
        source, trust = entry
        self.assertEqual(source.repository_url, "https://github.com/obra/superpowers")
        self.assertEqual(source.skill_path, "skills/verification-before-completion")
        self.assertEqual(source.commit_sha, "df2e996a174f49f05aa5d5777ca56fbb0aa972ec")
        self.assertEqual(source.license_spdx, "MIT")
        self.assertEqual(trust.state, "pinned")

        args = SimpleNamespace(terms=["scan", skill_id], registry=None, snapshot_dir=None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = handle_skill_command(args)
        self.assertEqual(code, 0)
        report = json.loads(out.getvalue())
        self.assertFalse(report["blocking"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sha256"], trust.sha256)

    def test_scan_rejects_snapshot_symlink(self):
        source = {
            "source_id": "demo", "skill_id": "demo",
            "repository_url": "https://github.com/example/skills", "skill_path": "demo",
            "commit_sha": "a" * 40, "license_spdx": "MIT",
        }
        snapshot_dir = Path(self.tmp.name) / "snapshot"
        snapshot_dir.mkdir()
        (snapshot_dir / "SKILL.md").symlink_to(Path(__file__))
        (self.root / "skill-sources.json").write_text(json.dumps({"schema_version": 1, "sources": [source]}), encoding="utf-8")
        (self.root / "skills.lock.json").write_text(json.dumps({
            "schema_version": 1,
            "skills": [{"skill_id": "demo", "source_id": "demo", "sha256": "b" * 64, "state": "discovered"}],
        }), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = handle_skill_command(self.args(["scan", "demo"], snapshot_dir=str(snapshot_dir)))
        self.assertEqual(code, 1)
        self.assertIn("symlink", err.getvalue())


if __name__ == "__main__":
    unittest.main()
