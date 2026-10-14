"""
InkFlow Quota and Word Limit Enforcement Service.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module implements the in-flight lazy quota reset and word consumption gate
adhering strictly to C:/InkFlow/docs/backend.md Section 5:

1. In-flight Lazy Reset Architecture:
   - Resets wordsUsedThisWeek to 0 whenever a new calendar week (Monday 00:00 UTC) has elapsed.
   - Calculates the exact start of the current week:
     start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
2. Free Tier Enforcement (2,500 Word Limit):
   - Users on 'free' tier are capped at 2,500 words per weekly cycle.
   - If incoming draft exceeds limit, returns 403 Forbidden with QUOTA_EXCEEDED payload.
3. Pro Tier Exemption:
   - Users on 'pro' tier enjoy unlimited rewrites.
================================================================================
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException, status
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_users_collection

logger = logging.getLogger("inkflow.quota")


class QuotaExceededException(HTTPException):
    """
    HTTP 403 Forbidden exception raised when a Free tier user exceeds their weekly word quota.
    Returns the exact JSON payload specified in docs/backend.md Section 5 & 8.
    """
    def __init__(self, words_used: int, limit: int, reset_date: Optional[datetime] = None) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "QUOTA_EXCEEDED",
                "message": "You've hit your weekly word limit.",
                "wordsUsed": words_used,
                "limit": limit,
                "resetsAt": "Monday 00:00 UTC",
                "upgradeRequired": True,
            },
        )


def count_words(text: str) -> int:
    """
    Accurately calculates word count by stripping whitespace and tokenizing words.
    
    Args:
        text: Input string.
        
    Returns:
        Integer word count.
    """
    if not text or not text.strip():
        return 0
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def calculate_next_monday_utc(current_time: datetime) -> datetime:
    """
    Calculates the exact upcoming Monday 00:00:00 UTC boundary.
    """
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    else:
        current_time = current_time.astimezone(timezone.utc)

    days_ahead = (0 - current_time.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7

    target_date = current_time.date() + timedelta(days=days_ahead)
    return datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=timezone.utc,
    )


def enforce_and_reset_quota(
    user: Dict[str, Any],
    requested_words: int,
) -> Tuple[Dict[str, Any], bool, Optional[str]]:
    """
    Checks if a new calendar week (Monday 00:00 UTC) has elapsed since lastWeekReset.
    If so, resets wordsUsedThisWeek to 0.
    Enforces word limits on Free tier users.
    
    Direct contract from docs/backend.md Section 5.
    
    Returns: (updated_user_dict, allowed, error_message)
    """
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    last_reset = user.get("lastWeekReset") or user.get("last_week_reset")
    if last_reset is not None and last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    # In-flight reset check: if no prior reset or reset was prior to current week start
    if last_reset is None or last_reset < start_of_week:
        user["wordsUsedThisWeek"] = 0
        user["words_used_this_week"] = 0
        user["lastWeekReset"] = start_of_week
        user["quota_reset_date"] = start_of_week + timedelta(days=7)

    # If Pro tier, allow unconditionally
    if user.get("tier") == "pro":
        return user, True, None

    limit = user.get("weeklyWordLimit", settings.FREE_TIER_WEEKLY_WORD_LIMIT)
    current_used = user.get("wordsUsedThisWeek", user.get("words_used_this_week", 0))

    if current_used + requested_words > limit:
        remaining = max(0, limit - current_used)
        error_msg = (
            f"Weekly limit reached ({current_used}/{limit} words used). "
            f"You have {remaining} words remaining this week. Upgrade to Pro for unlimited rewrites."
        )
        return user, False, error_msg

    return user, True, None


async def check_and_apply_quota(
    user_id: str,
    incoming_text: str,
) -> Tuple[Dict[str, Any], int, int]:
    """
    Asynchronous database-backed adapter for in-flight quota check and deduction.
    """
    users_col = get_users_collection()
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    words_to_consume = count_words(incoming_text)
    user, allowed, error_msg = enforce_and_reset_quota(user, words_to_consume)

    if not allowed:
        limit = user.get("weeklyWordLimit", 2500)
        current_used = user.get("wordsUsedThisWeek", 0)
        raise QuotaExceededException(words_used=current_used, limit=limit)

    now_utc = datetime.now(timezone.utc)
    current_used = user.get("wordsUsedThisWeek", 0)
    new_words_used = current_used + words_to_consume

    user["wordsUsedThisWeek"] = new_words_used
    user["words_used_this_week"] = new_words_used

    await users_col.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "wordsUsedThisWeek": new_words_used,
                "words_used_this_week": new_words_used,
                "lastWeekReset": user.get("lastWeekReset"),
                "updatedAt": now_utc,
                "updated_at": now_utc,
            }
        },
    )

    limit = user.get("weeklyWordLimit", 2500)
    user_tier = user.get("tier", "free")
    remaining_quota = max(0, limit - new_words_used) if user_tier == "free" else 999999

    return user, words_to_consume, remaining_quota
