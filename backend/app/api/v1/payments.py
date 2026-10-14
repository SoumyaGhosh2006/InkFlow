"""
InkFlow Subscription and Payment Management API Routes.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module manages monetization and subscription tier upgrades via Razorpay
adhering strictly to C:/InkFlow/docs/backend.md Section 8:

Endpoints:
- `POST /api/v1/payments/create-order`:
  Creates a Razorpay order for Pro upgrade (supports UPI, cards, netbanking).
- `POST /api/v1/payments/verify`:
  Validates Razorpay payment signature and upgrades user tier to 'pro'.
- `POST /api/v1/payments/webhook`:
  Receives asynchronous webhook notifications from payment processors.
================================================================================
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_users_collection
from app.core.security import get_current_user
from app.models.user import UserTier
from app.services.payments import payment_service

logger = logging.getLogger("inkflow.api.payments")
router = APIRouter()


class CreateOrderRequest(BaseModel):
    """Payload to initiate a Pro tier subscription checkout."""
    plan: str = Field(default="pro_monthly", description="Subscription plan identifier.")


class PaymentVerificationRequest(BaseModel):
    """Payload submitted from frontend checkout to confirm payment success."""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post(
    "/create-order",
    summary="Create Razorpay order for Pro subscription upgrade",
)
async def create_order(
    payload: CreateOrderRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    POST /api/v1/payments/create-order:
    Creates a Razorpay order for Pro upgrade (supports UPI, cards, netbanking).
    Contract defined in docs/backend.md Section 8.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    if current_user.get("tier") == UserTier.PRO.value:
        return {
            "status": "already_upgraded",
            "message": "User is already subscribed to the Pro tier.",
            "tier": "pro",
        }

    return payment_service.create_order(
        user_id=user_id,
        amount_cents=1500,
        currency="USD",
        plan=payload.plan,
    )


@router.post("/upgrade", summary="Alias for /create-order", include_in_schema=False)
async def upgrade_user(
    payload: CreateOrderRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Backward-compatible alias for /create-order."""
    return await create_order(payload, current_user)


@router.post(
    "/verify",
    summary="Validate Razorpay payment signature and upgrade user tier to pro",
)
async def verify_payment(
    payload: PaymentVerificationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    POST /api/v1/payments/verify:
    Validates Razorpay payment signature and upgrades user tier to pro.
    Contract defined in docs/backend.md Section 8.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    users_col = get_users_collection()

    is_valid = payment_service.verify_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature verification.",
        )

    now_utc = datetime.now(timezone.utc)
    await users_col.update_one(
        {"$or": [{"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else None}, {"userId": user_id}]},
        {
            "$set": {
                "tier": UserTier.PRO.value,
                "razorpaySubscriptionId": payload.razorpay_payment_id,
                "updatedAt": now_utc,
                "updated_at": now_utc,
            }
        },
    )

    logger.info("User %s successfully upgraded to PRO tier.", user_id)
    return {
        "status": "success",
        "message": "Congratulations! Your account has been upgraded to InkFlow Pro.",
        "tier": "pro",
    }


@router.post(
    "/webhook",
    summary="Asynchronous payment gateway webhook listener",
)
async def handle_payment_webhook(request: Request) -> Dict[str, str]:
    """
    Receives asynchronous webhooks from payment processors.
    """
    body = await request.body()
    logger.info("Received payment gateway webhook event: %d bytes", len(body))
    return {"status": "received"}
