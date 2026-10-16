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
        amount_cents=49900,
        currency="INR",
        plan="pro_monthly",
    )
    assert "order_id" in order
    assert order["amount"] == 49900
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
