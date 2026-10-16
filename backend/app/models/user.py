"""
InkFlow User Domain Model and Schemas.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module defines the User representation, subscription tiers, and quota
tracking fields for the InkFlow ecosystem adhering to docs/backend.md Section 7:

User Collection Schema:
- firebaseUid: Unique Firebase authentication UID.
- email: Primary email address.
- displayName: Human-readable display name.
- tier: 'free' (capped at 2,500 words/week) or 'pro' (unlimited).
- razorpaySubscriptionId: Optional subscription identifier.
- wordsUsedThisWeek: Counter for words processed during the current calendar week.
- weeklyWordLimit: 2500 words for Free tier.
- lastWeekReset: UTC timestamp of the most recent Monday 00:00:00 UTC cycle reset.
- streakDays: Current continuous active writing streak in days.
================================================================================
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


class UserTier(str, Enum):
    """
    Subscription tier levels governing word limits and feature access.
    """
    FREE = "free"
    PRO = "pro"


class UserBase(BaseModel):
    """
    Base attributes shared across user creation and response schemas.
    """
    email: EmailStr = Field(..., description="Unique email address of the user.")
    displayName: Optional[str] = Field(None, description="Display pseudonym or full name.")
    full_name: Optional[str] = Field(None, description="Backward-compatible alias for displayName.")


class UserCreate(UserBase):
    """
    Schema for user account creation or manual registration.
    """
    firebaseUid: Optional[str] = Field(None, description="Firebase Auth UID.")
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Optional password for non-Firebase local developer environments.",
    )


class AuthSyncRequest(BaseModel):
    """
    Schema for POST /api/v1/auth/sync endpoint.
    """
    firebaseUid: Optional[str] = Field(None, description="Firebase User UID.")
    email: Optional[EmailStr] = Field(None, description="Firebase User Email.")
    displayName: Optional[str] = Field(None, description="Firebase User Display Name.")


class UserLogin(BaseModel):
    """
    Schema for email/password authentication requests in local developer mode.
    """
    email: EmailStr = Field(..., description="Registered account email address.")
    password: str = Field(..., description="Account password.")


class UserUpdate(BaseModel):
    """
    Schema for updating user profile attributes.
    """
    displayName: Optional[str] = None
    tier: Optional[UserTier] = None


class UserResponse(BaseModel):
    """
    Public representation of a user account returned by API endpoints.
    """
    id: str = Field(..., description="Stringified MongoDB ObjectId.")
    firebaseUid: Optional[str] = Field(None, description="Firebase User UID.")
    email: str = Field(..., description="Registered email.")
    displayName: Optional[str] = Field(None, description="Display name.")
    tier: UserTier = Field(default=UserTier.FREE, description="Subscription tier ('free' or 'pro').")
    wordsUsedThisWeek: int = Field(default=0, description="Words consumed during current weekly cycle.")
    weeklyWordLimit: int = Field(default=1500, description="Daily word allowance (1,500 on Free tier).")
    lastWeekReset: datetime = Field(..., description="Monday 00:00:00 UTC boundary timestamp.")
    streakDays: int = Field(default=1, description="Consecutive writing streak days.")
    is_active: bool = Field(default=True, description="Account active flag.")
    created_at: datetime = Field(..., description="Timestamp of account registration.")

    # Aliases for backward compatibility with snake_case tests/clients
    @property
    def words_used_this_week(self) -> int:
        return self.wordsUsedThisWeek

    @property
    def quota_reset_date(self) -> datetime:
        return self.lastWeekReset

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "660c1bf6e4b09d2f8832a101",
                "firebaseUid": "firebase_uid_123",
                "email": "student@university.edu",
                "displayName": "Alex Mercer",
                "tier": "free",
                "wordsUsedThisWeek": 1420,
                "weeklyWordLimit": 2500,
                "lastWeekReset": "2026-10-12T00:00:00Z",
                "streakDays": 4,
                "is_active": True,
                "created_at": "2026-10-12T14:30:00Z",
            }
        },
    }


class Token(BaseModel):
    """
    Authentication token response returned upon successful authentication.
    """
    access_token: str = Field(..., description="Bearer token.")
    token_type: str = Field(default="bearer", description="Token scheme identifier.")
    user: UserResponse = Field(..., description="Associated authenticated user object.")
