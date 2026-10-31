"""Scenarios 1, 4 and the registry integrity checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import load_registry, patch_json
from omni.models import Skill
from omni.registry import Registry, RegistryError
from omni.routing import MissingSpecialty, Router


class TestClassification(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = load_registry(Path(self.tmp.name))
        self.router = Router(self.registry)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # Scenario 1 ---------------------------------------------------------
    def test_simple_request_selects_one_specialist(self) -> None:
        plan = self.router.plan("Ajoute un endpoint REST pour lister les utilisateurs")
        self.assertEqual(plan.classification.size, "simple")
        self.assertEqual(len(plan.assignments), 1)
        self.assertEqual(plan.assignments[0].agent_id, "omni-backend")
        self.assertEqual(plan.assignments[0].task.specialty, "backend-api")
        # the generalist fallback must not be used while a specialist exists
        self.assertNotIn("omni-generalist", plan.squad)

    # Scenario 2 ---------------------------------------------------------
    def test_complex_request_forms_squad(self) -> None:
        request = (
            "Refonte de bout en bout : API REST backend, interface React, tests, "
            "CI GitHub Actions, analyse des données, sécurité et revue de code"
        )
        plan = self.router.plan(request)
        self.assertEqual(plan.classification.size, "complex")
        self.assertGreaterEqual(len(plan.squad), 4)
        self.assertLessEqual(len(plan.squad), 8)
        specialties = {a.task.specialty for a in plan.assignments}
        for expected in {"backend-api", "frontend-ui", "testing-qa", "code-review"}:
            self.assertIn(expected, specialties)
        # reviewer runs in a later wave than the work it reviews
        review = next(a for a in plan.assignments if a.task.specialty == "code-review")
        self.assertEqual(review.wave, 2)
        self.assertTrue(review.task.depends_on)

    def test_medium_request_uses_one_to_three_agents(self) -> None:
        plan = self.router.plan("Corrige l'API REST et ajoute les tests unitaires")
        self.assertIn(plan.classification.size, ("medium", "simple"))
        self.assertLessEqual(len(plan.squad), 3)

    def test_no_trigger_defaults_to_research(self) -> None:
        plan = self.router.plan("xyzzy plugh")
        self.assertEqual(plan.classification.size, "simple")
        self.assertEqual(plan.assignments[0].task.specialty, "research-docs")

    # Scenario 4 ---------------------------------------------------------
    def test_missing_skill_suggests_existing_skills(self) -> None:
        def drop_android(dest: Path) -> None:
            def mutate_agents(data: dict) -> None:
                data["agents"] = [a for a in data["agents"] if a["id"] not in ("omni-android", "omni-generalist")]

            patch_json(dest / "agents.json", mutate_agents)

            def mutate_routing(data: dict) -> None:
                data["specialties"]["android"]["agents"] = ["omni-android"]
                data["specialties"]["android"]["fallbacks"] = []

            patch_json(dest / "routing.json", mutate_routing)

            def mutate_skills(data: dict) -> None:
                data["skills"].append(
                    {
                        "id": "android-skills-pack",
                        "title": "Android skills pack",
                        "source": "example/android-skills",
                        "verification": "unverified",
                        "specialties": ["android"],
                        "notes": "candidate found while searching for a missing skill",
                    }
                )

            patch_json(dest / "skills.json", mutate_skills)

        registry = load_registry(Path(self.tmp.name), drop_android)
        router = Router(registry)
        with self.assertRaises(MissingSpecialty) as ctx:
            router.select_agent("android")
        self.assertEqual(ctx.exception.specialty, "android")
        self.assertIn("android-skills-pack", ctx.exception.suggestions)

        # a plan keeps going and records the hole instead of crashing
        plan = router.plan("Crée une application Android avec Kotlin")
        self.assertIn("android", plan.unresolved_specialties)


class TestRegistryIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_shipped_registries_are_coherent(self) -> None:
        registry = load_registry(Path(self.tmp.name))
        problems = registry.validate()
        self.assertEqual(problems, [], f"registry problems: {problems}")

    def test_all_required_specialties_present(self) -> None:
        registry = load_registry(Path(self.tmp.name))
        required = set(registry.routing["required_specialties"])
        self.assertEqual(
            required,
            {
                "frontend-ui", "backend-api", "software-architecture", "android", "web-dev",
                "data-analysis", "research-docs", "security-defensive", "testing-qa",
                "debugging", "performance", "devops-ci", "github-repo", "design-ux",
                "ai-llm", "automation", "code-review", "orchestration",
            },
        )
        for sid in required:
            self.assertTrue(registry.agents_for(sid), f"no agent for {sid}")

    def test_validation_catches_broken_agent_reference(self) -> None:
        """The exact class of bug behind the optimiser-mes-agents-IA reference."""

        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["specialties"]["backend-api"]["agents"] = ["omni-ghost"]

            patch_json(dest / "routing.json", mutate)

        registry = load_registry(Path(self.tmp.name), break_it)
        problems = registry.validate()
        self.assertTrue(any("omni-ghost" in p for p in problems), problems)

    def test_validation_catches_agent_without_permissions(self) -> None:
        def break_it(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["agents"].pop("omni-qa")

            patch_json(dest / "permissions.json", mutate)

        registry = load_registry(Path(self.tmp.name), break_it)
        problems = registry.validate()
        self.assertTrue(any("omni-qa" in p for p in problems), problems)

    def test_duplicate_agent_id_is_rejected(self) -> None:
        def dupe(dest: Path) -> None:
            def mutate(data: dict) -> None:
                data["agents"].append(dict(data["agents"][0]))

            patch_json(dest / "agents.json", mutate)

        with self.assertRaises(RegistryError):
            load_registry(Path(self.tmp.name), dupe)

    def test_every_agent_documents_provenance(self) -> None:
        registry = load_registry(Path(self.tmp.name))
        for agent in registry.agents.values():
            self.assertTrue(agent.provenance, agent.id)

    def test_skills_marked_unverified_are_reported_as_such(self) -> None:
        registry = load_registry(Path(self.tmp.name))
        allowed = {"path-verified", "repo-exists", "unverified"}
        for skill in registry.skills.values():
            self.assertIn(skill.verification, allowed)
        # the shipped registry may not claim more than was checked
        self.assertGreater(
            sum(1 for s in registry.skills.values() if s.verification == "path-verified"), 0
        )


if __name__ == "__main__":
    unittest.main()
