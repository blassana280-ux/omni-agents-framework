"""Read-only, deterministic skill-ingestion contract tests."""
from __future__ import annotations

import unittest

from omni.skill_catalog import SkillCatalogError, SkillPolicy, SkillSource, ingest_skill


SOURCE = SkillSource(
    source_id="example-skill",
    skill_id="example-skill",
    repository_url="https://github.com/example/skills",
    skill_path="skills/example",
    commit_sha="a" * 40,
    license_spdx="MIT",
)


class SkillIngestionTests(unittest.TestCase):
    def setUp(self):
        self.files = {
            "SKILL.md": "---\nname: example-skill\ndescription: A safe test skill\nlicense: MIT\n---\n\nInstructions only.\n",
            "references/guide.md": "Reference text.\n",
        }

    def test_ingests_pinned_text_files_and_returns_deterministic_digest(self):
        result = ingest_skill(SOURCE, self.files)
        reversed_result = ingest_skill(SOURCE, dict(reversed(list(self.files.items()))))
        self.assertEqual(result.sha256, reversed_result.sha256)
        self.assertEqual(result.metadata["name"], "example-skill")
        self.assertEqual(result.metadata["description"], "A safe test skill")
        self.assertEqual(result.metadata["license"], "MIT")
        self.assertEqual(result.files, ("SKILL.md", "references/guide.md"))
        self.assertEqual(result.findings, ())

    def test_enforces_policy_file_and_byte_limits(self):
        with self.assertRaisesRegex(SkillCatalogError, "too many files"):
            ingest_skill(SOURCE, self.files, policy=SkillPolicy(max_files=1))
        with self.assertRaisesRegex(SkillCatalogError, "exceeds"):
            ingest_skill(SOURCE, self.files, policy=SkillPolicy(max_bytes=10))

    def test_requires_skill_markdown(self):
        with self.assertRaisesRegex(SkillCatalogError, "SKILL.md"):
            ingest_skill(SOURCE, {"README.md": "No skill definition"})

    def test_rejects_path_traversal_and_absolute_paths(self):
        for path in ("../outside.txt", "/tmp/escape.txt", "nested/../../escape.txt"):
            with self.subTest(path=path), self.assertRaises(SkillCatalogError):
                ingest_skill(SOURCE, {"SKILL.md": self.files["SKILL.md"], path: "bad"})

    def test_rejects_duplicate_normalized_paths(self):
        files = {"SKILL.md": self.files["SKILL.md"], "a/../SKILL.md": "shadow"}
        with self.assertRaisesRegex(SkillCatalogError, "path"):
            ingest_skill(SOURCE, files)

    def test_rejects_non_utf8_binary_payload(self):
        with self.assertRaisesRegex(SkillCatalogError, "UTF-8"):
            ingest_skill(SOURCE, {"SKILL.md": b"\xff\xfe"})

    def test_rejects_unpinned_source(self):
        unpinned = SkillSource(
            source_id="example-skill", skill_id="example-skill",
            repository_url=SOURCE.repository_url, skill_path=SOURCE.skill_path,
            commit_sha="main", license_spdx="MIT",
        )
        with self.assertRaisesRegex(SkillCatalogError, "commit SHA"):
            ingest_skill(unpinned, self.files)

    def test_rejects_duplicate_path_aliases_after_normalization(self):
        files = {
            "SKILL.md": self.files["SKILL.md"],
            "references/./guide.md": "one",
            "references/guide.md": "two",
        }
        with self.assertRaisesRegex(SkillCatalogError, "duplicate"):
            ingest_skill(SOURCE, files)


    def test_rejects_windows_drive_absolute_paths(self):
        with self.assertRaisesRegex(SkillCatalogError, "absolute"):
            ingest_skill(SOURCE, {
                "SKILL.md": self.files["SKILL.md"],
                "C:/outside.txt": "must not be accepted",
            })


if __name__ == "__main__":
    unittest.main()
