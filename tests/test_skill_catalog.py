"""Contract tests for the versioned skill catalog."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omni.skill_catalog import SkillCatalog, SkillCatalogError, SkillSource, SkillTrustRecord

COMMIT = "a" * 40
DIGEST = "b" * 64


def write_catalog(root: Path, *, sources=None, skills=None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    default_source = {
        "source_id": "agent-skills-spec",
        "skill_id": "agent-skills-spec",
        "repository_url": "https://github.com/agentskills/agentskills",
        "skill_path": "docs/specification",
        "commit_sha": COMMIT,
        "license_spdx": "MIT",
        "upstream_identity": "agentskills",
        "maintainer": None,
    }
    default_lock = {
        "skill_id": "agent-skills-spec",
        "source_id": "agent-skills-spec",
        "sha256": DIGEST,
        "state": "discovered",
    }
    (root / "skill-sources.json").write_text(
        json.dumps({"schema_version": 1, "sources": sources if sources is not None else [default_source]}),
        encoding="utf-8",
    )
    (root / "skills.lock.json").write_text(
        json.dumps({"schema_version": 1, "skills": skills if skills is not None else [default_lock]}),
        encoding="utf-8",
    )
    return root


class SkillCatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_catalog(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_loads_valid_pinned_source_and_lock(self):
        catalog = SkillCatalog.load(self.root)
        entry = catalog.get("agent-skills-spec")
        self.assertIsNotNone(entry)
        source, trust = entry
        self.assertIsInstance(source, SkillSource)
        self.assertIsInstance(trust, SkillTrustRecord)
        self.assertEqual(source.commit_sha, COMMIT)
        self.assertEqual(trust.sha256, DIGEST)
        self.assertEqual(trust.state, "discovered")
        self.assertEqual(catalog.validate(), [])

    def test_rejects_missing_commit_sha(self):
        source = json.loads((self.root / "skill-sources.json").read_text())["sources"][0]
        del source["commit_sha"]
        write_catalog(self.root, sources=[source])
        with self.assertRaisesRegex(SkillCatalogError, "commit_sha"):
            SkillCatalog.load(self.root)

    def test_rejects_malformed_digest(self):
        lock = json.loads((self.root / "skills.lock.json").read_text())["skills"][0]
        lock["sha256"] = "not-a-sha256"
        write_catalog(self.root, skills=[lock])
        with self.assertRaisesRegex(SkillCatalogError, "sha256"):
            SkillCatalog.load(self.root)

    def test_rejects_duplicate_skill_ids(self):
        source = json.loads((self.root / "skill-sources.json").read_text())["sources"][0]
        duplicate = dict(source, source_id="duplicate-source")
        write_catalog(self.root, sources=[source, duplicate])
        with self.assertRaisesRegex(SkillCatalogError, "duplicate skill_id"):
            SkillCatalog.load(self.root)

    def test_rejects_duplicate_source_identities(self):
        source = json.loads((self.root / "skill-sources.json").read_text())["sources"][0]
        duplicate = dict(source, skill_id="other-skill", source_id="other-source")
        lock1 = json.loads((self.root / "skills.lock.json").read_text())["skills"][0]
        lock2 = dict(lock1, skill_id="other-skill", source_id="other-source")
        write_catalog(self.root, sources=[source, duplicate], skills=[lock1, lock2])
        with self.assertRaisesRegex(SkillCatalogError, "duplicate source identity"):
            SkillCatalog.load(self.root)

    def test_rejects_unknown_lifecycle_state(self):
        lock = json.loads((self.root / "skills.lock.json").read_text())["skills"][0]
        lock["state"] = "trusted-by-default"
        write_catalog(self.root, skills=[lock])
        with self.assertRaisesRegex(SkillCatalogError, "state"):
            SkillCatalog.load(self.root)

    def test_rejects_lock_record_without_source(self):
        lock = json.loads((self.root / "skills.lock.json").read_text())["skills"][0]
        lock["source_id"] = "missing-source"
        write_catalog(self.root, skills=[lock])
        with self.assertRaisesRegex(SkillCatalogError, "source_id"):
            SkillCatalog.load(self.root)

    def test_rejects_malformed_json(self):
        (self.root / "skills.lock.json").write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(SkillCatalogError, "invalid JSON"):
            SkillCatalog.load(self.root)

    def test_legacy_registry_without_rich_metadata_remains_loadable(self):
        (self.root / "skills.json").write_text(
            json.dumps({"skills": [{
                "id": "legacy-skill",
                "title": "Legacy",
                "source": "old/repo",
                "specialties": ["research-docs"],
                "verification": "repo-exists",
            }]}),
            encoding="utf-8",
        )
        catalog = SkillCatalog.load(self.root)
        self.assertIsNone(catalog.get("legacy-skill"))
        self.assertIsNotNone(catalog.get("agent-skills-spec"))

    def test_rejects_unsupported_schema_version(self):
        (self.root / "skill-sources.json").write_text(
            json.dumps({"schema_version": 2, "sources": []}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SkillCatalogError, "schema_version"):
            SkillCatalog.load(self.root)


if __name__ == "__main__":
    unittest.main()
