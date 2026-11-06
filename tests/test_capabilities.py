"""Registre des capacités : validation, découverte, routage, mémoire des résultats.

Couvre les exigences de la mission OMNIBRAIN GITHUB CAPABILITY EXPANSION :
identifiant, description, prérequis, permissions, tests et statut
d'intégration pour chaque capacité ; validation des licences ; détection de
secrets ; routage vers les agents spécialistes ; journal des résultats.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import copy_registry, patch_json
from omni.capabilities import (
    CapabilityError,
    CapabilityLedger,
    CapabilityRegistry,
    redact,
)
from omni.capabilities import main as capabilities_main
from omni.registry import Registry


def load_shipped(tmp_path: Path):
    """Registres livrés copiés en bac à sable : registre agents + capacités."""
    dest = copy_registry(tmp_path)
    return dest, Registry.load(dest), CapabilityRegistry.load(dest)


class TestShippedRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest, self.registry, self.caps = load_shipped(Path(self.tmp.name))

    def test_shipped_registry_validates(self) -> None:
        known = list(self.registry.routing["specialties"].keys())
        problems = self.caps.validate(known_specialties=known)
        self.assertEqual(problems, [], f"capability registry problems: {problems}")

    def test_every_capability_declares_the_mission_fields(self) -> None:
        """Identifiant, description, prérequis, permissions, tests, statut."""
        for cap in self.caps.capabilities.values():
            self.assertTrue(cap.id, "missing id")
            self.assertTrue(cap.title, f"{cap.id}: missing title")
            self.assertTrue(cap.description, f"{cap.id}: missing description")
            self.assertTrue(cap.prerequisites, f"{cap.id}: missing prerequisites")
            self.assertIsInstance(cap.permissions_needed, list)
            self.assertTrue(cap.tests, f"{cap.id}: missing tests")
            self.assertTrue(cap.status, f"{cap.id}: missing integration status")

    def test_external_capabilities_declare_permissive_licenses(self) -> None:
        allowed = set(self.caps.data["licenses_allowed"])
        for cap in self.caps.capabilities.values():
            if cap.upstream:
                self.assertIn(cap.license_spdx, allowed, cap.id)

    def test_forks_pending_are_external_only(self) -> None:
        pending = self.caps.forks_pending()
        self.assertTrue(pending, "expected pending external capabilities")
        for cap in pending:
            self.assertTrue(cap.upstream, cap.id)
            self.assertEqual(cap.status, "indexed")

    def test_status_report_counts(self) -> None:
        report = self.caps.status_report()
        self.assertEqual(report["total"], len(self.caps.capabilities))
        self.assertEqual(report["by_status"].get("verified", 0), 3)
        self.assertTrue(report["forks_pending"])


class TestValidationGates(unittest.TestCase):
    """Chaque règle de validation doit réellement attraper le défaut ciblé."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _caps(self, mutate=None) -> CapabilityRegistry:
        dest = copy_registry(Path(self.tmp.name), mutate)
        return CapabilityRegistry.load(dest)

    def test_duplicate_capability_id_is_rejected(self) -> None:
        def dupe(dest: Path) -> None:
            patch_json(dest / "capabilities.json", lambda d: d["capabilities"].append(dict(d["capabilities"][0])))

        with self.assertRaises(CapabilityError):
            self._caps(dupe)

    def test_validate_catches_unknown_status(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["integration"]["status"] = "wishful-thinking"
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("unknown status" in p for p in problems), problems)

    def test_validate_catches_unknown_domain(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["domain"] = "teleportation"
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("unknown domain" in p for p in problems), problems)

    def test_validate_catches_disallowed_license(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["license"]["spdx"] = "GPL-3.0"
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("licenses_allowed" in p for p in problems), problems)

    def test_validate_catches_forked_without_fork(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                cap = data["capabilities"][0]
                cap["integration"]["status"] = "forked"
                cap["source"]["fork"] = None
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("requires a fork reference" in p for p in problems), problems)

    def test_validate_catches_verified_without_evidence_or_test(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                cap = data["capabilities"][0]
                cap["integration"]["status"] = "verified"
                cap["integration"]["evidence"] = []
                cap["tests"] = [{"name": "x", "status": "not-run"}]
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("requires evidence" in p for p in problems), problems)
        self.assertTrue(any("passing test" in p for p in problems), problems)

    def test_validate_catches_missing_entry_points(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["entry_points"] = []
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(break_it).validate()
        self.assertTrue(any("entry_points" in p for p in problems), problems)

    def test_validate_catches_unknown_routing_specialty(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["specialties"] = ["telepathy"]
            patch_json(dest / "capabilities.json", mutate)

        registry = Registry.load(copy_registry(Path(self.tmp.name)))
        known = list(registry.routing["specialties"].keys())
        problems = self._caps(break_it).validate(known_specialties=known)
        self.assertTrue(any("unknown routing specialty" in p for p in problems), problems)

    def test_secrets_in_registry_are_detected(self) -> None:
        def contaminate(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["description"] += " ghp_0123456789ABCDEF0123456789ABCDEF0123 leak"
            patch_json(dest / "capabilities.json", mutate)

        problems = self._caps(contaminate).validate()
        self.assertTrue(any("secret pattern" in p for p in problems), problems)


class TestDiscoveryRouting(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest, self.registry, self.caps = load_shipped(Path(self.tmp.name))

    def test_search_by_terms_finds_capability(self) -> None:
        hits = self.caps.search(["navigateur"])
        self.assertIn("browser-use-agentic", [c.id for c in hits])

    def test_search_by_domain_filters(self) -> None:
        hits = self.caps.search([], domain="research-deep")
        ids = [c.id for c in hits]
        self.assertIn("gpt-researcher-deepsearch", ids)
        self.assertNotIn("browser-use-agentic", ids)

    def test_by_domain_groups_capabilities(self) -> None:
        groups = self.caps.by_domain()
        self.assertIn("browser-automation", groups)
        self.assertIn("reasoning-planning", groups)
        for domain, caps in groups.items():
            for cap in caps:
                self.assertEqual(cap.domain, domain)

    def test_entry_points_give_lazy_loading_directives(self) -> None:
        paths = self.caps.entry_paths("browser-use-agentic")
        self.assertTrue(paths)
        first = paths[0]
        self.assertEqual(first["repo"], "browser-use/browser-use")
        self.assertEqual(first["path"], "README.md")
        for directive in paths:
            self.assertTrue(directive["repo"], "lazy loading needs a repo")
            self.assertTrue(directive["path"])
            self.assertTrue(directive["purpose"])

    def test_unknown_capability_entry_points_raise(self) -> None:
        with self.assertRaises(CapabilityError):
            self.caps.entry_paths("does-not-exist")

    def test_suggest_agents_routes_to_specialists(self) -> None:
        agents = self.caps.suggest_agents("browser-use-agentic", self.registry)
        self.assertTrue(agents, "expected at least one agent covering 'automation'")
        for agent_id in agents:
            self.assertIn(agent_id, self.registry.agents)

    def test_dependency_report_lists_dependencies(self) -> None:
        report = self.caps.dependency_report()
        self.assertIn("whisper-transcription", report)
        self.assertIn("ffmpeg", report["whisper-transcription"])


class TestResultsLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = CapabilityLedger(Path(self.tmp.name) / "ledger" / "capability-results.jsonl")

    def test_record_and_history_roundtrip(self) -> None:
        self.ledger.record("browser-use-agentic", "ok", "scenario E2E exécuté", ["trace:ok"])
        self.ledger.record("browser-use-agentic", "error", "timeout navigateur", ["log:42"])
        history = self.ledger.history("browser-use-agentic")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["outcome"], "ok")
        self.assertEqual(history[1]["outcome"], "error")

    def test_history_filters_by_capability(self) -> None:
        self.ledger.record("a", "ok")
        self.ledger.record("b", "ok")
        self.assertEqual(len(self.ledger.history("a")), 1)
        self.assertEqual(len(self.ledger.history()), 2)
        self.assertEqual(self.ledger.history("missing"), [])

    def test_ledger_never_stores_secrets(self) -> None:
        entry = self.ledger.record(
            "litellm-routing", "ok", "clé ghp_0123456789ABCDEF0123456789ABCDEF0123 branchée"
        )
        self.assertIn("[REDACTED]", entry["summary"])
        self.assertNotIn("ghp_0123456789ABCDEF0123456789ABCDEF0123", entry["summary"])
        # rien ne fuit pas non plus depuis le disque
        stored = self.ledger.history("litellm-routing")[0]["summary"]
        self.assertNotIn("ghp_", stored)

    def test_invalid_outcome_is_rejected(self) -> None:
        with self.assertRaises(CapabilityError):
            self.ledger.record("a", "maybe")

    def test_redact_handles_common_secret_shapes(self) -> None:
        self.assertIn("[REDACTED]", redact("sk-0123456789abcdef"))
        self.assertIn("[REDACTED]", redact("AKIAIOSFODNN7EXAMPLE"))
        self.assertNotIn("AKIA", redact("AKIAIOSFODNN7EXAMPLE"))
        self.assertEqual(redact("rien à signaler"), "rien à signaler")


class TestCLI(unittest.TestCase):
    """La CLI accepte les deux formes : --validate (drapeau) et validate (positionnel)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _run(self, argv, mutate=None) -> int:
        dest = copy_registry(Path(self.tmp.name), mutate)
        return capabilities_main(["--registry", str(dest)] + argv)

    def test_validate_flag_on_clean_registry_exits_zero(self) -> None:
        self.assertEqual(self._run(["--validate"]), 0)

    def test_validate_flag_detects_problems_and_exits_one(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["capabilities"][0]["integration"]["status"] = "wishful-thinking"
            patch_json(dest / "capabilities.json", mutate)

        self.assertEqual(self._run(["--validate"], break_it), 1)

    def test_unknown_action_exits_two(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self._run(["--nonsense"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
