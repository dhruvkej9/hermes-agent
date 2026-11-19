"""A provider 200 whose body is not JSON is a provider fault: retried, and another provider may take it."""

import json

from agent.error_classifier import FailoverReason, classify_api_error


def test_json_decode_error_is_an_incomplete_response_that_falls_back():
    verdict = classify_api_error(json.JSONDecodeError("Expecting value", "", 0), provider="custom")

    assert verdict.reason is FailoverReason.incomplete_response
    assert verdict.retryable and verdict.should_fallback
