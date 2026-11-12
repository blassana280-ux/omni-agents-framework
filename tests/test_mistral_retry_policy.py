"""Mistral calls are never replayed automatically inside the same run."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import load_registry
from omni.models import ProviderResult
from omni.orchestrator import Orchestrator


SIMPLE = "Ajoute un endpoint REST pour lister les utilisateurs"


class StubProvider:
    def __init__(self, name, response):
        self.name = name
        self.response = response
        self.calls = []

    def available(self):
        return True, "stub provider"

    def execute(self, brief, workdir=None):
        self.calls.append(brief.attempt)
        return self.response(brief)


class TestMistralRetryPolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = load_registry(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, provider):
        orch = Orchestrator(
            self.registry,
            provider,
            workspace=self.root,
            state_dir=self.root / ".omni",
            retries=2,
            correction_rounds=2,
        )
        return orch.run(SIMPLE)

    def test_mistral_http_429_is_not_retried_or_reassigned(self):
        provider = StubProvider(
            "mistral",
            lambda brief: ProviderResult(
                status="failed",
                error="Mistral API HTTP 429: rate limit or quota reached",
                executed=False,
                provider="mistral",
            ),
        )

        record = self.run_with(provider)

        self.assertEqual(provider.calls, [1])
        self.assertEqual(len(record.results), 1)
        self.assertNotIn("retry", [event["event"] for event in record.trace])
        self.assertNotIn("reassign", [event["event"] for event in record.trace])
        self.assertEqual(record.corrections, [])

    def test_mistral_incomplete_result_is_not_sent_to_correction_loop(self):
        provider = StubProvider(
            "mistral",
            lambda brief: ProviderResult(
                status="incomplete",
                summary="Unverified model response",
                executed=True,
                provider="mistral",
            ),
        )

        record = self.run_with(provider)

        self.assertEqual(provider.calls, [1])
        self.assertEqual(len(record.results), 1)
        self.assertEqual(record.corrections, [])
        self.assertNotIn("correction_request", [event["event"] for event in record.trace])

    def test_other_providers_keep_retry_and_correction_behavior(self):
        def response(brief):
            if brief.attempt == 1:
                return ProviderResult(
                    status="failed",
                    error="temporary scripted failure",
                    executed=False,
                    provider="scripted-double",
                )
            if brief.attempt == 2:
                return ProviderResult(
                    status="ok",
                    summary="First successful response is incomplete",
                    evidence=["initial"],
                    met_criteria=[],
                    executed=True,
                    provider="scripted-double",
                )
            return ProviderResult(
                status="ok",
                summary="Corrected response",
                evidence=["corrected"],
                met_criteria=list(brief.acceptance_criteria),
                executed=True,
                provider="scripted-double",
            )

        provider = StubProvider("scripted-double", response)
        record = self.run_with(provider)

        self.assertEqual(provider.calls, [1, 2, 3])
        self.assertIn("retry", [event["event"] for event in record.trace])
        self.assertTrue(record.corrections)


if __name__ == "__main__":
    unittest.main()
