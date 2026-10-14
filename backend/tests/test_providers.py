"""
InkFlow Automated Tests: Two-Tier Groq Provider Failover and Granular Timeout Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the fault-tolerant orchestration of LLM providers:
1. Primary Success:
   - When Groq Llama 3.3 70B responds normally, returns text tagged 'groq_llama33'.
2. Connect Timeout Failover:
   - When Primary encounters `httpx.ConnectTimeout` (2.5s limit), seamlessly calls Groq Llama 3.1 8B
     and tags response as 'groq_llama31_8b'.
3. Read Timeout Failover:
   - When Primary exceeds read timeout (9.0s), failover to Groq Llama 3.1 8B succeeds without user-facing error.
4. HTTP Status 500 Failover:
   - When Primary returns HTTP 500 internal server error, failover to fallback succeeds.
5. Total Outage Raising:
   - When both Primary (70B) and Fallback (8B) fail, raises `LLMProviderError`.
6. Contract Function (`generate_llm_completion`):
   - Verifies the standalone tuple-returning function contract defined in backend.md Section 3.
================================================================================
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.providers import (
    ResilientLLMService,
    LLMProviderError,
    LLMResult,
    generate_llm_completion,
)


@pytest.mark.asyncio
async def test_primary_provider_success():
    """
    Verifies that when primary Groq openai/gpt-oss-120b responds successfully,
    the result is properly tagged as 'groq_gpt_oss_120b'.
    """
    service = ResilientLLMService()
    expected_output = "Clear and punchy authentic text without any slop."

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback:
        mock_primary.return_value = expected_output

        result: LLMResult = await service.complete([{"role": "user", "content": "Hello"}])

        assert result.text == expected_output
        assert result.provider == "groq_gpt_oss_120b"
        assert result.duration_ms >= 0.0
        mock_primary.assert_awaited_once()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_primary_connect_timeout_failover_to_fallback():
    """
    Verifies that when the primary model times out during TCP handshake (connect timeout),
    the service immediately fails over to Groq openai/gpt-oss-20b and tags output as 'groq_gpt_oss_20b'.
    """
    service = ResilientLLMService()
    fallback_output = "Fallback text generated swiftly by Groq openai/gpt-oss-20b."

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = httpx.ConnectTimeout("Connect timeout to primary model")
        mock_fallback.return_value = fallback_output

        result: LLMResult = await service.complete([{"role": "user", "content": "Test"}])

        assert result.text == fallback_output
        assert result.provider == "groq_gpt_oss_20b"
        mock_primary.assert_awaited_once()
        mock_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_primary_read_timeout_failover_to_fallback():
    """
    Verifies that when the primary model hangs on generation (read timeout > 9.0s),
    the request seamlessly routes to Groq openai/gpt-oss-20b.
    """
    service = ResilientLLMService()
    fallback_output = "Groq output succeeding after primary read timeout."

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = httpx.ReadTimeout("Primary read timeout > 9.0s")
        mock_fallback.return_value = fallback_output

        result: LLMResult = await service.complete([{"role": "user", "content": "Test"}])

        assert result.text == fallback_output
        assert result.provider == "groq_gpt_oss_20b"
        mock_primary.assert_awaited_once()
        mock_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_primary_http_error_failover():
    """
    Verifies that when the primary model returns HTTP 500 error,
    it triggers immediate failover to fallback model.
    """
    service = ResilientLLMService()
    fallback_output = "Groq rescue completion."

    dummy_request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    dummy_response = httpx.Response(status_code=500, request=dummy_request)

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = httpx.HTTPStatusError("500 Internal Server Error", request=dummy_request, response=dummy_response)
        mock_fallback.return_value = fallback_output

        result: LLMResult = await service.complete([{"role": "user", "content": "Test"}])

        assert result.text == fallback_output
        assert result.provider == "groq_gpt_oss_20b"
        mock_primary.assert_awaited_once()
        mock_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_both_providers_fail_raises_llm_provider_error():
    """
    Verifies that when BOTH primary (120B) and fallback (20B) fail,
    the service cleanly raises an LLMProviderError.
    """
    service = ResilientLLMService()

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = httpx.ConnectTimeout("Primary unreachable")
        mock_fallback.side_effect = httpx.ReadTimeout("Fallback also timed out")

        with pytest.raises(LLMProviderError) as exc_info:
            await service.complete([{"role": "user", "content": "Test"}])

        assert "All LLM providers exhausted" in str(exc_info.value)
        mock_primary.assert_awaited_once()
        mock_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_llm_completion_contract():
    """
    Verifies that generate_llm_completion returns tuple (text, provider_tag).
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Sample generated text"}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        text, provider = await generate_llm_completion(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
        )

        assert text == "Sample generated text"
        assert provider == "groq_gpt_oss_120b"


@pytest.mark.asyncio
async def test_groq_429_rate_limit_triggers_sentry_alert():
    """
    Verifies that an HTTP 429 rate limit from Groq triggers Sentry tag
    'error.type': 'groq_rate_limit_429' and logs a critical rate limit alert.
    """
    service = ResilientLLMService()

    dummy_req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    dummy_resp = httpx.Response(status_code=429, request=dummy_req)
    rate_limit_exc = httpx.HTTPStatusError("429 Too Many Requests", request=dummy_req, response=dummy_resp)

    with patch.object(service, "_call_primary", new_callable=AsyncMock) as mock_primary, \
         patch.object(service, "_call_fallback", new_callable=AsyncMock) as mock_fallback, \
         patch("sentry_sdk.set_tag") as mock_set_tag, \
         patch("sentry_sdk.capture_message") as mock_capture_message:

        mock_primary.side_effect = rate_limit_exc
        mock_fallback.return_value = "Recovered by fallback"

        result = await service.complete([{"role": "user", "content": "Test"}])

        assert result.provider == "groq_gpt_oss_20b"
        # Verify Sentry was tagged with rate limit error type
        mock_set_tag.assert_any_call("error.type", "groq_rate_limit_429")
        mock_set_tag.assert_any_call("llm.rate_limit_hit", "true")
        # Verify critical Sentry message was captured
        mock_capture_message.assert_any_call(
            "CRITICAL: Groq API Rate Limit (HTTP 429) encountered on Primary (openai/gpt-oss-120b). Shared key pool may be exhausted.",
            level="error",
        )

