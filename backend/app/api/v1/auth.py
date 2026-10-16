"""
InkFlow Authentication and Account Management API Routes.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module provides user profile synchronization and authentication routes
adhering strictly to C:/InkFlow/docs/backend.md Section 8:

Endpoints:
- `POST /api/v1/auth/sync`:
  Verifies Firebase Bearer token and creates or retrieves user profile in MongoDB.
  Initializes wordsUsedThisWeek to 0 and lastWeekReset to Monday 00:00:00 UTC.
- `GET /api/v1/auth/me`:
  Returns authenticated user profile and active quota metrics.
================================================================================
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_users_collection
from app.core.security import get_current_user
from app.models.user import (
    UserResponse,
    UserTier,
    AuthSyncRequest,
    UserCreate,
    UserLogin,
    Token,
)

logger = logging.getLogger("inkflow.auth")
router = APIRouter()


def _format_user_response(user_doc: Dict[str, Any]) -> UserResponse:
    """Transforms a raw MongoDB document into a typed UserResponse."""
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    user_id = str(user_doc.get("_id", ""))
    tier = UserTier(user_doc.get("tier", "free"))
    limit = 999999 if tier == UserTier.PRO else getattr(settings, "FREE_TIER_DAILY_WORD_LIMIT", 1500)
    return UserResponse(
        id=user_id,
        firebaseUid=user_doc.get("firebaseUid"),
        email=user_doc.get("email", ""),
        displayName=user_doc.get("displayName") or user_doc.get("full_name"),
        tier=tier,
        wordsUsedThisWeek=user_doc.get("wordsUsedThisWeek", user_doc.get("words_used_this_week", 0)),
        weeklyWordLimit=limit,
        lastWeekReset=user_doc.get("lastWeekReset", start_of_week),
        streakDays=user_doc.get("streakDays", 1),
        is_active=user_doc.get("is_active", True),
        created_at=user_doc.get("createdAt", user_doc.get("created_at", now)),
    )


@router.post(
    "/sync",
    response_model=UserResponse,
    summary="Sync user profile from Firebase Auth token",
)
async def sync_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """
    POST /api/v1/auth/sync:
    Verifies Firebase Bearer token and creates or retrieves user profile in MongoDB.
    Contract defined in docs/backend.md Section 8.
    """
    logger.info("Synchronized user profile for: %s", current_user.get("email"))
    return _format_user_response(current_user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve authenticated user profile and active quota",
)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """
    Returns current authenticated profile and quota status.
    """
    return _format_user_response(current_user)
