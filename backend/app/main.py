"""
InkFlow FastAPI Main Application Gateway.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This is the root application entrypoint for the InkFlow backend service:

Key Architectural Features:
1. Lifespan Context Manager:
   - Manages asynchronous resource lifecycles: establishes the Motor MongoDB
     connection pool and builds collection indexes on startup; gracefully terminates
     socket connections on shutdown.
2. Cross-Origin Resource Sharing (CORS):
   - Configures secure CORS headers allowing frontend client communication across
     authorized domains (localhost:3000, production domains).
3. Centralized Exception Handlers:
   - Handles `QuotaExceededException` (HTTP 429) returning detailed reset countdowns.
   - Handles `LLMProviderError` (HTTP 503) when upstream inference is degraded.
4. Sentry Telemetry:
   - Bootstraps Sentry performance monitoring and distributed pipeline tracing.
================================================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.sentry import init_sentry
from app.api.v1 import api_v1_router
from app.services.quota import QuotaExceededException
from app.services.providers import LLMProviderError

# Configure root application logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("inkflow.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Asynchronous lifespan manager handling startup and shutdown lifecycles.
    
    1. Startup: Initializes Sentry telemetry and establishes MongoDB connection pool.
    2. Shutdown: Gracefully drains and closes MongoDB connection sockets.
    """
    logger.info("Initializing InkFlow Backend (%s mode)...", settings.ENVIRONMENT)
    
    # Bootstrap Sentry observability
    init_sentry()
    
    # Establish persistent connection pool to MongoDB
    await connect_to_mongo()
    
    yield
    
    # Teardown database connections cleanly
    logger.info("Shutting down InkFlow Backend...")
    await close_mongo_connection()


# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Adaptive writing twin and anti-AI-slop assistant API for university students and professionals.",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# Middleware Configuration: CORS
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Custom Exception Handlers
# ------------------------------------------------------------------------------
@app.exception_handler(QuotaExceededException)
async def quota_exceeded_handler(request: Request, exc: QuotaExceededException) -> JSONResponse:
    """
    Formats HTTP 403 quota exhaustion responses strictly adhering to backend.md Section 5.
    """
    content = exc.detail if isinstance(exc.detail, dict) else {"status": "QUOTA_EXCEEDED", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
    """
    Formats HTTP 503 errors when primary and fallback LLMs are unreachable.
    """
    logger.error("LLM Provider outage: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "LLM_SERVICE_UNAVAILABLE",
            "detail": "Upstream AI inference engines are temporarily unavailable. Please retry in a few moments.",
        },
    )


# ------------------------------------------------------------------------------
# Route Registration
# ------------------------------------------------------------------------------
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check() -> dict:
    """
    Lightweight health check endpoint for container orchestrators and load balancers.
    """
    return {
        "status": "healthy",
        "service": "inkflow-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
