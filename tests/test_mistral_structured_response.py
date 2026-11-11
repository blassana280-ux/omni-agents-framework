"""Contract tests for structured Mistral responses; all HTTP is mocked."""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from unittest import mock

from omni.executor import MistralProvider, _NoRedirectHandler, _open_no_redirect
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
    def test_redirect_handler_rejects_redirects(self):
        handler = _NoRedirectHandler()
        request = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=b"{}",
            headers={"Authorization": "Bearer synthetic-secret"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as raised:
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": "https://attacker.example/collect"},
                "https://attacker.example/collect",
            )

        self.assertEqual(raised.exception.code, 302)
        self.assertEqual(raised.exception.filename, request.full_url)

    def test_open_no_redirect_uses_the_blocking_handler(self):
        request = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=b"{}",
            headers={"Authorization": "Bearer synthetic-secret"},
            method="POST",
        )
        fake_response = FakeResponse({})
        opener = mock.Mock()
        opener.open.return_value = fake_response

        with mock.patch("urllib.request.build_opener", return_value=opener) as build:
            response = _open_no_redirect(request, timeout=17)

        self.assertIs(response, fake_response)
        self.assertIsInstance(build.call_args.args[0], _NoRedirectHandler)
        opener.open.assert_called_once_with(request, timeout=17)

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
            "omni.executor._open_no_redirect", return_value=FakeResponse(payload)
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
            "omni.executor._open_no_redirect", return_value=FakeResponse(payload)
        ):
            result = MistralProvider.from_env().execute(brief)

        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.met_criteria, [])
        self.assertEqual(result.claims["verification"], "unverified_model_output")
        self.assertEqual(result.claims["model_reported_criteria"], ["[REDACTED]"])
        self.assertNotIn(secret, str(result.to_dict()))


    def test_http_endpoint_is_rejected_before_sending_api_key(self):
        secret = "test-secret-key-not-a-pattern"
        provider = MistralProvider(
            api_key=secret,
            allow_paid=True,
            endpoint="http://attacker.example/v1/chat/completions",
        )
        brief = Brief(
            task_id="mistral-insecure-endpoint",
            agent_id="omni-research",
            specialty="research",
            objective="Never send credentials over HTTP",
            acceptance_criteria=[],
            allowed_tools=[],
            boundaries=[],
        )
        with mock.patch("omni.executor._open_no_redirect") as send:
            result = provider.execute(brief)

        send.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.executed)
        self.assertNotIn(secret, str(result.to_dict()))
        self.assertIn("HTTPS", result.error)

    def test_non_mistral_https_host_is_rejected_before_sending_api_key(self):
        secret = "test-secret-key-not-a-pattern"
        provider = MistralProvider(
            api_key=secret,
            allow_paid=True,
            endpoint="https://attacker.example/v1/chat/completions",
        )
        brief = Brief(
            task_id="mistral-untrusted-host",
            agent_id="omni-research",
            specialty="research",
            objective="Never send the API key to an untrusted host",
            acceptance_criteria=[],
            allowed_tools=[],
            boundaries=[],
        )
        with mock.patch("omni.executor._open_no_redirect") as send:
            result = provider.execute(brief)

        send.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.executed)
        self.assertNotIn(secret, str(result.to_dict()))

    def test_endpoint_with_embedded_credentials_is_rejected(self):
        provider = MistralProvider(
            api_key="test-secret-key-not-a-pattern",
            allow_paid=True,
            endpoint="https://user:password@api.mistral.ai/v1/chat/completions",
        )
        brief = Brief(
            task_id="mistral-userinfo-endpoint",
            agent_id="omni-research",
            specialty="research",
            objective="Reject credential-bearing endpoints",
            acceptance_criteria=[],
            allowed_tools=[],
            boundaries=[],
        )
        with mock.patch("omni.executor._open_no_redirect") as send:
            result = provider.execute(brief)

        send.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertIn("endpoint", result.error.lower())


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
            "omni.executor._open_no_redirect", return_value=FakeResponse(payload)
        ) as send:
            result = MistralProvider.from_env().execute(brief)

        self.assertEqual(result.status, "incomplete")
        request = send.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        user_prompt = body["messages"][1]["content"]
        self.assertNotIn(secret, user_prompt)
        self.assertNotIn("another-super-secret-value", user_prompt)
        self.assertIn("[REDACTED]", user_prompt)


    def test_network_timeout_marks_provider_effect_unknown(self):
        secret = "test-secret-key-not-a-pattern"
        brief = Brief(
            task_id="mistral-network-timeout",
            agent_id="omni-research",
            specialty="research",
            objective="Classify an ambiguous provider timeout safely",
            acceptance_criteria=[],
            allowed_tools=[],
            boundaries=[],
        )
        with mock.patch.dict(os.environ, {
            "MISTRAL_API_KEY": secret,
            "OMNI_MISTRAL_ALLOW_PAID": "1",
        }, clear=True), mock.patch(
            "omni.executor._open_no_redirect", side_effect=TimeoutError("read timed out")
        ):
            result = MistralProvider.from_env().execute(brief)

        self.assertEqual(result.status, "effect_unknown")
        self.assertFalse(result.executed)
        self.assertIn("network_request=attempted", result.evidence)
        self.assertIn("provider_effect=unknown", result.evidence)
        self.assertIn("automatic_retry=blocked", result.evidence)
        self.assertNotIn(secret, str(result.to_dict()))


if __name__ == "__main__":
    unittest.main()
