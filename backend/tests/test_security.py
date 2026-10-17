"""
Tests for Core Security, Token Verification, and Authentication Guards.
"""

from datetime import datetime, timezone, timedelta
from jose import jwt
from app.core.config import settings
from app.core.security import verify_firebase_or_jwt_token, create_access_token


def test_verify_valid_internal_jwt():
    """Verify signed internal HS256 tokens decode properly."""
    token = create_access_token({"sub": "usr_internal_123", "email": "test@inkflow.app"})
    claims = verify_firebase_or_jwt_token(token)
    assert claims is not None
    assert claims.get("sub") == "usr_internal_123"
    assert claims.get("email") == "test@inkflow.app"


def test_test_tokens_allowed_in_dev_rejected_in_prod():
    """Mock tokens (test_*, mock_*) must work in dev but be blocked in production."""
    old_env = settings.ENVIRONMENT
    old_debug = settings.DEBUG
    try:
        # Development mode
        settings.ENVIRONMENT = "development"
        settings.DEBUG = True
        dev_claims = verify_firebase_or_jwt_token("test_user_999")
        assert dev_claims is not None
        assert dev_claims.get("uid") == "test_user_999"

        # Production mode
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False
        prod_claims = verify_firebase_or_jwt_token("test_user_999")
        assert prod_claims is None
    finally:
        settings.ENVIRONMENT = old_env
        settings.DEBUG = old_debug


def test_production_token_expiry_enforced():
    """Tokens with past expiration must be rejected in production."""
    old_env = settings.ENVIRONMENT
    old_debug = settings.DEBUG
    try:
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False

        past_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        expired_token = jwt.encode(
            {"sub": "usr_exp", "email": "exp@example.com", "exp": past_ts, "aud": "inkstop-7cad9"},
            "arbitrary_key",
            algorithm="HS256",
        )
        claims = verify_firebase_or_jwt_token(expired_token)
        assert claims is None
    finally:
        settings.ENVIRONMENT = old_env
        settings.DEBUG = old_debug


def test_production_token_audience_mismatch_rejected():
    """Tokens for a different Firebase project must be rejected in production."""
    old_env = settings.ENVIRONMENT
    old_debug = settings.DEBUG
    old_pid = settings.FIREBASE_PROJECT_ID
    try:
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False
        settings.FIREBASE_PROJECT_ID = "inkstop-7cad9"

        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        foreign_token = jwt.encode(
            {"sub": "usr_attacker", "email": "attacker@evil.com", "exp": future_ts, "aud": "evil-foreign-project"},
            "arbitrary_key",
            algorithm="HS256",
        )
        claims = verify_firebase_or_jwt_token(foreign_token)
        assert claims is None

        # Matching audience should succeed
        valid_token = jwt.encode(
            {"sub": "usr_valid", "email": "valid@example.com", "exp": future_ts, "aud": "inkstop-7cad9"},
            "arbitrary_key",
            algorithm="HS256",
        )
        valid_claims = verify_firebase_or_jwt_token(valid_token)
        assert valid_claims is not None
        assert valid_claims.get("sub") == "usr_valid"
    finally:
        settings.ENVIRONMENT = old_env
        settings.DEBUG = old_debug
        settings.FIREBASE_PROJECT_ID = old_pid
