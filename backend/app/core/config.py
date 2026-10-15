"""
InkFlow Core Configuration Module.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module centralizes all environment-specific and deployment-wide configuration
parameters for the InkFlow backend. Using Pydantic V2's `BaseSettings`, it provides:
1. Strict type validation across environment variables.
2. Default fail-safes for local development environments.
3. Two-tier Groq LLM configuration:
   - Primary: llama-3.3-70b-versatile (70B deep reasoning, high stylistic fidelity)
   - Fallback: llama-3.1-8b-instant (8B sub-second instant failover)
4. Granular connection and read timeout specifications:
   - Primary: connect=2.5s, read=9.0s
   - Fallback: connect=2.0s, read=8.0s
5. Weekly word quota constants (2,500 words for Free Tier resetting Mondays 00:00 UTC).
================================================================================
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    
    Attributes:
        PROJECT_NAME: Human-readable name of the service.
        ENVIRONMENT: Current deployment stage (development, staging, production).
        DEBUG: Boolean flag indicating if debug mode is active.
        API_V1_STR: Base URL prefix for version 1 API routes.
        SECRET_KEY: Cryptographic key used for signing JWT authentication tokens.
        ALGORITHM: Token hashing algorithm, defaulting to HMAC SHA-256.
        ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of issued JWT tokens (e.g. 7 days).
        MONGODB_URI: Full connection string for asynchronous MongoDB instance.
        MONGODB_DB_NAME: Active database namespace for user, genome, and logs storage.
        GROQ_BASE_URL: Base URL for Groq OpenAI-compatible API gateway.
        GROQ_API_KEY: Authentication bearer token for Groq API.
        GROQ_PRIMARY_MODEL: Primary model identifier (openai/gpt-oss-120b).
        GROQ_FALLBACK_MODEL: Fallback model identifier (openai/gpt-oss-20b).
        PRIMARY_CONNECT_TIMEOUT: Granular connect timeout for primary inference (2.5s).
        PRIMARY_READ_TIMEOUT: Maximum time allowed to stream/generate tokens (9.0s).
        FALLBACK_CONNECT_TIMEOUT: Connect timeout for secondary provider (2.0s).
        FALLBACK_READ_TIMEOUT: Read timeout for secondary provider (8.0s).
        FREE_TIER_WEEKLY_WORD_LIMIT: Word quota allocated per week to Free users.
        SENTRY_DSN: Sentry telemetry endpoint for tracking unhandled errors and spans.
        SENTRY_TRACES_SAMPLE_RATE: Sampling percentage for performance transactions.
        PAYMENT_PROVIDER: Active payment processor ('razorpay').
        RAZORPAY_KEY_ID: Public API key for Razorpay checkout integration.
        RAZORPAY_KEY_SECRET: Webhook and signature secret for Razorpay transactions.
        CORS_ORIGINS: List of allowed origins for cross-origin resource sharing.
    """

    # --- Project Metadata ---
    PROJECT_NAME: str = "InkFlow API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # --- Cryptography & Session Tokens ---
    SECRET_KEY: str = "inkflow-insecure-development-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days default

    # --- Database (Motor Async MongoDB) ---
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "inkflow"

    # --- Two-Tier Groq Provider Setup ---
    # Primary: openai/gpt-oss-120b (deep reasoning, high stylistic precision)
    # Fallback: openai/gpt-oss-20b (blazing fast, resilient backup)
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-20b"

    # Backward compatibility alias
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Granular timeouts
    PRIMARY_CONNECT_TIMEOUT: float = 3.5
    PRIMARY_READ_TIMEOUT: float = 15.0
    FALLBACK_CONNECT_TIMEOUT: float = 5.0
    FALLBACK_READ_TIMEOUT: float = 15.0

    # Secondary backward compatibility aliases
    GROQ_CONNECT_TIMEOUT: float = 2.0
    GROQ_READ_TIMEOUT: float = 8.0

    # --- Quota and Limit Rules ---
    FREE_TIER_WEEKLY_WORD_LIMIT: int = 2500

    # --- Observability & Telemetry ---
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0

    # --- Payments & Tier Upgrades ---
    PAYMENT_PROVIDER: str = "razorpay"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # --- Cross-Origin Resource Sharing (CORS) ---
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://inkflow.app",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parses comma-separated string representations into a validated list of origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
