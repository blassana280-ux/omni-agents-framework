"""Contract tests for structured Mistral responses; all HTTP is mocked."""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from omni.executor import MistralProvider
from omni.models import Brief


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit=-1):
        return self.payload


class TestMistralStructuredResponse(unittest.TestCase):
    def test_structured_output_filters_criteria_and_redacts_exact_key(self):
        brief = Brief(
            task_id="mistral-test",
            agent_id="omni-research",
            specialty="research",
            objective="Summarize provided context",
            acceptance_criteria=["criterion_one", "criterion_two"],
            allowed_tools=[],
            boundaries=["Do not claim external tool use"],
        )
        secret = "test-secret-key-not-a-pattern"
        content = json.dumps({
            "summary": f"Structured answer with {secret}",
            "evidence": ["The supplied brief was processed"],
            "met_criteria": ["criterion_one", "invented_criterion"],
            "artifacts": [],
            "claims": {"source": "provided context"},
        })
        payload = {
            "id": "req-contract-123",
            "model": "mistral-small-latest",
            "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
            "choices": [{"message": {"content": content}}],
        }
        with mock.patch.dict(os.environ, {
            "OMNI_PROVIDER": "mistral",
            "MISTRAL_API_KEY": secret,
            "OMNI_MISTRAL_ALLOW_PAID": "1",
        }, clear=True), mock.patch(
            "urllib.request.urlopen", return_value=FakeResponse(payload)
        ) as send:
            provider = MistralProvider.from_env()
            result = provider.execute(brief)

        self.assertTrue(result.executed)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.summary, "Structured answer with [REDACTED]")
        self.assertEqual(result.met_criteria, [])
        self.assertEqual(result.claims["verification"], "unverified_model_output")
        self.assertEqual(
            result.claims["model_reported_criteria"],
            ["criterion_one", "invented_criterion"],
        )
        self.assertEqual(result.claims["model_evidence"], ["The supplied brief was processed"])
        self.assertNotIn(secret, str(result.to_dict()))
        self.assertIn("mistral_request_id=req-contract-123", result.evidence)
        self.assertTrue(any("total_tokens=46" in item for item in result.evidence))
        request = send.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["response_format"], {"type": "json_object"})



    def test_exact_api_key_is_redacted_from_accepted_criteria(self):
        secret = "test-secret-key-not-a-pattern"
        brief = Brief(
            task_id="mistral-redaction",
            agent_id="omni-research",
            specialty="research",
            objective="Check secret redaction",
            acceptance_criteria=[secret],
            allowed_tools=[],
            boundaries=[],
        )
        payload = {
            "choices": [{
                "message": {"content": json.dumps({
                    "summary": "ok",
                    "evidence": [],
                    "met_criteria": [secret],
                    "artifacts": [],
                    "claims": {},
                })}
            }]
        }
        with mock.patch.dict(os.environ, {
            "MISTRAL_API_KEY": secret,
            "OMNI_MISTRAL_ALLOW_PAID": "1",
        }, clear=True), mock.patch(
            "urllib.request.urlopen", return_value=FakeResponse(payload)
        ):
            result = MistralProvider.from_env().execute(brief)

        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.met_criteria, [])
        self.assertEqual(result.claims["verification"], "unverified_model_output")
        self.assertEqual(result.claims["model_reported_criteria"], ["[REDACTED]"])
        self.assertNotIn(secret, str(result.to_dict()))


    def test_brief_is_redacted_before_remote_request(self):
        secret = "test-secret-key-not-a-pattern"
        brief = Brief(
            task_id="mistral-input-redaction",
            agent_id="omni-research",
            specialty="research",
            objective=f"Process this credential: {secret}; also api_key=another-super-secret-value",
            acceptance_criteria=[secret],
            allowed_tools=[],
            boundaries=[],
        )
        payload = {
            "choices": [{
                "message": {"content": json.dumps({
                    "summary": "ok",
                    "evidence": [],
                    "met_criteria": [],
                    "artifacts": [],
                    "claims": {},
                })}
            }]
        }
        with mock.patch.dict(os.environ, {
            "MISTRAL_API_KEY": secret,
            "OMNI_MISTRAL_ALLOW_PAID": "1",
        }, clear=True), mock.patch(
            "urllib.request.urlopen", return_value=FakeResponse(payload)
        ) as send:
            result = MistralProvider.from_env().execute(brief)

        self.assertEqual(result.status, "incomplete")
        request = send.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        user_prompt = body["messages"][1]["content"]
        self.assertNotIn(secret, user_prompt)
        self.assertNotIn("another-super-secret-value", user_prompt)
        self.assertIn("[REDACTED]", user_prompt)


if __name__ == "__main__":
    unittest.main()
