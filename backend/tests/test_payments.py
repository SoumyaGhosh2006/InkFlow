"""
Tests for Razorpay Order Creation and Cryptographic Payment Signature Verification.
"""

import hmac
import hashlib
import pytest
from app.services.payments import payment_service
from app.core.config import settings


@pytest.mark.asyncio
async def test_create_order_valid():
    """Verify order creation succeeds with order_id, amount, and currency."""
    order = await payment_service.create_order(
        user_id="usr_test_123",
        amount_cents=3900,
        currency="INR",
        plan="pro_monthly",
    )
    assert "order_id" in order
    assert order["amount"] == 3900
    assert order["currency"] == "INR"


@pytest.mark.asyncio
async def test_create_order_minimum_amount_rejected():
    """Verify order creation rejects amounts below 100 paise (₹1)."""
    with pytest.raises(ValueError, match="Minimum order amount"):
        await payment_service.create_order(
            user_id="usr_test_123",
            amount_cents=50,
        )


def test_verify_signature_valid():
    """Verify valid HMAC-SHA256 signature returns True."""
    secret = settings.RAZORPAY_KEY_SECRET or "ctKv3GEqc31zZzuW5v5MnLO0"
    order_id = "order_test_123"
    payment_id = "pay_test_456"

    # Compute valid signature
    message = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # Temporarily set key secret if needed for testing
    old_secret = settings.RAZORPAY_KEY_SECRET
    try:
        settings.RAZORPAY_KEY_SECRET = secret
        assert payment_service.verify_signature(order_id, payment_id, valid_sig) is True
    finally:
        settings.RAZORPAY_KEY_SECRET = old_secret


def test_verify_signature_invalid():
    """Verify tampered signature returns False."""
    secret = settings.RAZORPAY_KEY_SECRET or "ctKv3GEqc31zZzuW5v5MnLO0"
    order_id = "order_test_123"
    payment_id = "pay_test_456"
    bad_sig = "invalid_tampered_signature_hex"

    old_secret = settings.RAZORPAY_KEY_SECRET
    try:
        settings.RAZORPAY_KEY_SECRET = secret
        assert payment_service.verify_signature(order_id, payment_id, bad_sig) is False
    finally:
        settings.RAZORPAY_KEY_SECRET = old_secret


def test_verify_signature_missing_fields():
    """Verify missing fields are rejected immediately."""
    assert payment_service.verify_signature("", "pay_123", "sig_123") is False
    assert payment_service.verify_signature("order_123", "", "sig_123") is False
    assert payment_service.verify_signature("order_123", "pay_123", "") is False


@pytest.mark.asyncio
async def test_verify_payment_endpoint_db_failure_raises_500():
    """Verify that a database update failure raises HTTP 500 instead of returning false success."""
    from unittest.mock import patch, AsyncMock
    from fastapi import HTTPException
    from app.api.v1.payments import verify_payment, PaymentVerificationRequest

    payload = PaymentVerificationRequest(
        razorpay_order_id="order_123",
        razorpay_payment_id="pay_123",
        razorpay_signature="valid_mock_sig",
    )
    current_user = {"_id": "usr_test_123", "email": "test@inkflow.app", "tier": "free"}

    with patch.object(payment_service, "verify_signature", return_value=True):
        with patch("app.api.v1.payments.get_users_collection") as mock_col:
            mock_col.return_value.update_one = AsyncMock(side_effect=Exception("MongoDB connection timeout"))
            with pytest.raises(HTTPException) as exc_info:
                await verify_payment(payload, current_user)
            assert exc_info.value.status_code == 500
            assert "failed to persist Pro subscription" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_payment_endpoint_success():
    """Verify successful verification updates tier in DB and returns pro tier."""
    from unittest.mock import patch, AsyncMock
    from app.api.v1.payments import verify_payment, PaymentVerificationRequest

    payload = PaymentVerificationRequest(
        razorpay_order_id="order_123",
        razorpay_payment_id="pay_123",
        razorpay_signature="valid_mock_sig",
    )
    current_user = {"_id": "usr_test_123", "email": "test@inkflow.app", "tier": "free"}

    with patch.object(payment_service, "verify_signature", return_value=True):
        with patch("app.api.v1.payments.get_users_collection") as mock_col:
            mock_col.return_value.update_one = AsyncMock(return_value=None)
            res = await verify_payment(payload, current_user)
            assert res["status"] == "success"
            assert res["tier"] == "pro"

