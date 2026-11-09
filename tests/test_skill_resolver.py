"""Trust-gated deterministic skill resolution tests."""
from __future__ import annotations

import unittest

from omni.skill_catalog import (
    SkillApproval,
    SkillCatalog,
    SkillPolicy,
    SkillSource,
    SkillTrustRecord,
    ingest_skill,
)
from omni.skill_resolver import resolve_skills, resolution_to_dict


class SkillResolverTests(unittest.TestCase):
    def make_entry(
        self, skill_id="security-review", *, state="approved", license_spdx="MIT",
        content=None, approval=True, record_digest=None,
    ):
        source = SkillSource(
            source_id=f"source-{skill_id}",
            skill_id=skill_id,
            repository_url="https://github.com/example/skills",
            skill_path=skill_id,
            commit_sha="a" * 40,
            license_spdx=license_spdx,
        )
        body = content or (
            "---\n"
            f"name: {skill_id}\n"
            "description: Review Python code for security and reliability risks\n"
            "license: MIT\n"
            "---\n"
            "Use read-only analysis and report evidence.\n"
        )
        snapshot = ingest_skill(source, {"SKILL.md": body})
        digest = record_digest or snapshot.sha256
        approval_record = SkillApproval(
            approver="reviewer", digest=digest, reference="PR-18 review"
        ) if approval else None
        record = SkillTrustRecord(
            skill_id=skill_id, source_id=source.source_id, sha256=digest,
            state=state, approval=approval_record,
        )
        catalog = SkillCatalog({source.source_id: source}, {skill_id: record})
        return catalog, source, record, snapshot

    def test_approved_intact_non_blocking_skill_is_ranked(self):
        catalog, _, _, snapshot = self.make_entry()
        result = resolve_skills("review Python security", catalog, {"security-review": snapshot})
        self.assertEqual([item.skill_id for item in result.matches], ["security-review"])
        self.assertEqual(result.matches[0].matched_terms, ("python", "review", "security"))
        self.assertEqual(result.matches[0].state, "approved")
        self.assertEqual(result.excluded_counts["trust_state"], 0)

    def test_pinned_skill_is_filtered_before_relevance_and_scan(self):
        dangerous = "---\nname: security-review\ndescription: review security\n---\nrm -rf /tmp/demo\n"
        catalog, _, _, snapshot = self.make_entry(state="pinned", content=dangerous, approval=False)
        result = resolve_skills("review security", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["trust_state"], 1)
        self.assertEqual(result.excluded_counts["blocking_static_scan"], 0)

    def test_approved_state_without_digest_bound_human_approval_is_excluded(self):
        catalog, _, _, snapshot = self.make_entry(approval=False)
        result = resolve_skills("review security", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["missing_approval"], 1)

    def test_unsupported_license_is_excluded(self):
        catalog, _, _, snapshot = self.make_entry(license_spdx="GPL-3.0")
        result = resolve_skills("review security", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["unsupported_license"], 1)

    def test_digest_mismatch_is_excluded(self):
        other_digest = "b" * 64
        catalog, _, _, snapshot = self.make_entry(record_digest=other_digest)
        result = resolve_skills("review security", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["integrity_mismatch"], 1)

    def test_blocking_static_scan_excludes_skill(self):
        dangerous = "---\nname: security-review\ndescription: review security\nlicense: MIT\n---\nrm -rf /tmp/demo\n"
        catalog, _, _, snapshot = self.make_entry(content=dangerous)
        result = resolve_skills("review security", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["blocking_static_scan"], 1)

    def test_missing_snapshot_is_excluded(self):
        catalog, _, _, _ = self.make_entry()
        result = resolve_skills("review security", catalog, {})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["missing_snapshot"], 1)

    def test_irrelevant_skill_is_not_recommended(self):
        catalog, _, _, snapshot = self.make_entry()
        result = resolve_skills("create an animation", catalog, {"security-review": snapshot})
        self.assertEqual(result.matches, ())
        self.assertEqual(result.excluded_counts["no_relevant_terms"], 1)

    def test_result_is_deterministic_and_never_executes(self):
        first, _, _, first_snapshot = self.make_entry("alpha-review")
        second, _, _, second_snapshot = self.make_entry("beta-review")
        sources = {}
        records = {}
        for catalog in (second, first):
            for source, record in catalog.items():
                sources[source.source_id] = source
                records[record.skill_id] = record
        combined = SkillCatalog(sources, records)
        result = resolve_skills(
            "review Python security", combined,
            {"alpha-review": first_snapshot, "beta-review": second_snapshot},
            max_results=1,
        )
        self.assertEqual(result.eligible_count, 2)
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.matches[0].skill_id, "alpha-review")
        self.assertEqual(resolution_to_dict(result)["executions_performed"], 0)

    def test_empty_or_non_searchable_request_is_rejected(self):
        catalog, _, _, snapshot = self.make_entry()
        with self.assertRaisesRegex(ValueError, "non-empty text"):
            resolve_skills("   ", catalog, {"security-review": snapshot})
        with self.assertRaisesRegex(ValueError, "searchable term"):
            resolve_skills("the and with", catalog, {"security-review": snapshot})


if __name__ == "__main__":
    unittest.main()
