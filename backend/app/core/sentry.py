"""
InkFlow Core Sentry Observability and Agent Tracing Module.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module integrates Sentry performance monitoring and distributed tracing
specifically tailored for multi-stage LLM agent pipelines:
1. Sentry SDK Initialization: Safely bootstraps Sentry with FastAPI integration,
   filtering out health check noise while capturing trace spans for rewrite stages.
2. `trace_pipeline_stage`: An async context manager that records execution latency,
   custom tags (such as provider used, prompt tokens, and validation status), and
   reports unhandled pipeline crashes with full stack trace context.
================================================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import settings

logger = logging.getLogger("inkflow.sentry")


def init_sentry() -> None:
    """
    Initializes Sentry telemetry if a valid SENTRY_DSN is configured.
    
    Configures automatic transaction profiling and FastAPI route instrumentation.
    If SENTRY_DSN is empty, logs a diagnostic notice and continues without overhead.
    """
    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN is not configured. Running without Sentry telemetry.")
        return

    logger.info("Initializing Sentry tracing with environment: %s", settings.ENVIRONMENT)
    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
            ],
            # Avoid sending PII in automated error logs
            send_default_pii=False,
            # Attach stack trace to all log messages of WARNING or ERROR
            attach_stacktrace=True,
        )
        logger.info("Sentry initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize Sentry SDK: %s", exc, exc_info=True)


@asynccontextmanager
async def trace_pipeline_stage(
    stage_name: str,
    tags: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[Optional[Any], None]:
    """
    Asynchronous context manager creating a distributed tracing span for pipeline stages.
    
    Usage:
        async with trace_pipeline_stage("stage_3_meaning_check", {"attempt": 1}) as span:
            # stage execution logic
            ...

    Args:
        stage_name: Descriptive identifier of the pipeline stage (e.g., 'stage_1_generate').
        tags: Optional key-value dictionary to attach to the span.
        
    Yields:
        The active Sentry span instance, or None if Sentry is disabled.
    """
    tags = tags or {}
    
    # Check if Sentry is actively enabled (Sentry SDK 2.x standard)
    is_active = bool(sentry_sdk.is_initialized())

    if is_active:
        with sentry_sdk.start_span(op="pipeline.stage", description=stage_name) as span:
            # Record custom tags for observability analysis
            for key, val in tags.items():
                span.set_tag(key, str(val))
            try:
                yield span
            except Exception as exc:
                # Capture exception in the active span and record tag
                span.set_tag("pipeline.error", True)
                span.set_data("error_message", str(exc))
                sentry_sdk.capture_exception(exc)
                raise
    else:
        # Fallback when Sentry is unconfigured: simple no-op yielding None
        yield None
