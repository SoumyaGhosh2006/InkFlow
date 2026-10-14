"""
InkFlow Resilient LLM Providers Module.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module implements high-availability, two-tier LLM completion orchestration
using the Groq API:

Primary vs Fallback Matrix:
- Primary Provider: llama-3.3-70b-versatile via Groq Cloud API
  Connect Timeout: 2.5s (fail-fast on network latency/unreachable gateway)
  Read Timeout: 9.0s (active inference limit)
  Provider Tag: 'groq_llama33'
- Fallback Provider: llama-3.1-8b-instant via Groq Cloud API
  Connect Timeout: 2.0s
  Read Timeout: 8.0s (sub-second instant generation)
  Provider Tag: 'groq_llama31_8b'

Telemetry and Monitoring:
- Automatically injects Sentry tags ('llm.provider') and captures failover warning events.
- Raises RuntimeError / LLMProviderError when both models fail.
================================================================================
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import httpx
import sentry_sdk
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("inkflow.providers")

# Granular timeout configurations
PRIMARY_TIMEOUT = httpx.Timeout(
    connect=settings.PRIMARY_CONNECT_TIMEOUT,
    read=settings.PRIMARY_READ_TIMEOUT,
    write=5.0,
    pool=5.0,
)
FALLBACK_TIMEOUT = httpx.Timeout(
    connect=settings.FALLBACK_CONNECT_TIMEOUT,
    read=settings.FALLBACK_READ_TIMEOUT,
    write=5.0,
    pool=5.0,
)


class LLMResult(BaseModel):
    """
    Standardized result payload returned by LLM completion calls.
    
    Attributes:
        text: Raw generated or transformed output from the language model.
        provider: Provider identifier ('groq_llama33' or 'groq_llama31_8b').
        duration_ms: Wall-clock duration of the request in milliseconds.
    """
    text: str
    provider: str
    duration_ms: float


class LLMProviderError(Exception):
    """
    Raised when both the primary and fallback LLM providers fail to produce a completion.
    """
    pass


async def generate_llm_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Tuple[str, str]:
    """
    Attempts Groq Llama 3.3 70B first. If connection fails or times out,
    transparently falls back to Groq Llama 3.1 8B.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'.
        temperature: Sampling temperature for generation randomness.
        max_tokens: Maximum tokens allowed for generation.
        
    Returns:
        Tuple of (generated_text, provider_tag).
        
    Raises:
        RuntimeError / LLMProviderError: If both LLM providers fail.
    """
    groq_base = settings.GROQ_BASE_URL.rstrip("/")
    groq_url = f"{groq_base}/chat/completions" if groq_base.endswith("/v1") else f"{groq_base}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    # --------------------------------------------------------------------------
    # 1. Attempt Primary: Groq Llama 3.3 70B Versatile
    # --------------------------------------------------------------------------
    try:
        async with httpx.AsyncClient(timeout=PRIMARY_TIMEOUT) as client:
            response = await client.post(
                groq_url,
                headers=headers,
                json={
                    "model": settings.GROQ_PRIMARY_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            try:
                sentry_sdk.set_tag("llm.provider", "groq_llama33")
            except Exception:
                pass
            return content, "groq_llama33"

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        is_429 = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
        if is_429:
            try:
                sentry_sdk.set_tag("error.type", "groq_rate_limit_429")
                sentry_sdk.set_tag("llm.rate_limit_hit", "true")
                sentry_sdk.capture_message(
                    "CRITICAL: Groq API Rate Limit (HTTP 429) encountered on Primary (llama-3.3-70b-versatile). Shared key pool may be exhausted.",
                    level="error",
                )
            except Exception:
                pass

        logger.warning(
            "Primary Groq Llama 3.3 failed (%s: %s). Failing over to Groq Llama 3.1 8B.",
            type(exc).__name__,
            exc,
        )
        try:
            sentry_sdk.capture_message(
                f"Primary Groq Llama 3.3 failed ({type(exc).__name__}). Failing over to Llama 3.1 8B.",
                level="warning",
            )
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # 2. Resilient Fallback: Groq Llama 3.1 8B Instant
    # --------------------------------------------------------------------------
    try:
        async with httpx.AsyncClient(timeout=FALLBACK_TIMEOUT) as client:
            response = await client.post(
                groq_url,
                headers=headers,
                json={
                    "model": settings.GROQ_FALLBACK_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            try:
                sentry_sdk.set_tag("llm.provider", "groq_llama31_8b")
            except Exception:
                pass
            return content, "groq_llama31_8b"

    except Exception as exc:
        is_429 = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
        if is_429:
            try:
                sentry_sdk.set_tag("error.type", "groq_rate_limit_429")
                sentry_sdk.set_tag("llm.rate_limit_hit", "true")
                sentry_sdk.capture_message(
                    "CRITICAL: Groq API Rate Limit (HTTP 429) encountered on Fallback (llama-3.1-8b-instant). Shared API key pool completely exhausted.",
                    level="error",
                )
            except Exception:
                pass

        logger.error("Fallback Groq Llama 3.1 8B also failed: %s", exc)
        try:
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass
        raise LLMProviderError(f"Both LLM providers failed: {exc}") from exc


class ResilientLLMService:
    """
    Adapter service providing duration tracking and backward-compatible helper methods.
    """

    def __init__(self) -> None:
        self.primary_timeout = PRIMARY_TIMEOUT
        self.fallback_timeout = FALLBACK_TIMEOUT

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResult:
        """
        Executes completion with provider failover and records wall-clock latency.
        """
        t0 = time.monotonic()
        # Direct delegation to internal provider calls to permit mock interception in tests
        try:
            text = await self._call_primary(messages, temperature, max_tokens)
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            try:
                sentry_sdk.set_tag("llm.provider", "groq_llama33")
            except Exception:
                pass
            return LLMResult(
                text=text,
                provider="groq_llama33",
                duration_ms=round(elapsed_ms, 2),
            )
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPStatusError, httpx.RequestError) as exc:
            is_429 = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
            if is_429:
                try:
                    sentry_sdk.set_tag("error.type", "groq_rate_limit_429")
                    sentry_sdk.set_tag("llm.rate_limit_hit", "true")
                    sentry_sdk.capture_message(
                        "CRITICAL: Groq API Rate Limit (HTTP 429) encountered on Primary (llama-3.3-70b-versatile). Shared key pool may be exhausted.",
                        level="error",
                    )
                except Exception:
                    pass
            logger.warning("Primary failed (%s). Failing over to Groq Llama 3.1 8B.", type(exc).__name__)
            try:
                sentry_sdk.capture_message(
                    f"Primary Groq Llama 3.3 failed ({type(exc).__name__}). Failing over to Llama 3.1 8B.",
                    level="warning",
                )
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Unexpected primary failure (%s). Failing over.", exc)

        try:
            text = await self._call_fallback(messages, temperature, max_tokens)
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            try:
                sentry_sdk.set_tag("llm.provider", "groq_llama31_8b")
            except Exception:
                pass
            return LLMResult(
                text=text,
                provider="groq_llama31_8b",
                duration_ms=round(elapsed_ms, 2),
            )
        except Exception as exc:
            is_429 = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
            if is_429:
                try:
                    sentry_sdk.set_tag("error.type", "groq_rate_limit_429")
                    sentry_sdk.set_tag("llm.rate_limit_hit", "true")
                    sentry_sdk.capture_message(
                        "CRITICAL: Groq API Rate Limit (HTTP 429) encountered on Fallback (llama-3.1-8b-instant). Shared API key pool completely exhausted.",
                        level="error",
                    )
                except Exception:
                    pass
            try:
                sentry_sdk.capture_exception(exc)
            except Exception:
                pass
            raise LLMProviderError(f"All LLM providers exhausted: {exc}") from exc

    async def _call_primary(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Calls Groq Cloud Llama 3.3 70B primary endpoint."""
        groq_base = settings.GROQ_BASE_URL.rstrip("/")
        groq_url = f"{groq_base}/chat/completions" if groq_base.endswith("/v1") else f"{groq_base}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.primary_timeout) as client:
            response = await client.post(
                groq_url,
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={
                    "model": settings.GROQ_PRIMARY_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _call_fallback(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Calls Groq Cloud Llama 3.1 8B fallback endpoint."""
        groq_base = settings.GROQ_BASE_URL.rstrip("/")
        groq_url = f"{groq_base}/chat/completions" if groq_base.endswith("/v1") else f"{groq_base}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.fallback_timeout) as client:
            response = await client.post(
                groq_url,
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={
                    "model": settings.GROQ_FALLBACK_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    # Backward compatibility alias
    _call_groq = _call_fallback


# Module singleton instance
resilient_llm_service = ResilientLLMService()
