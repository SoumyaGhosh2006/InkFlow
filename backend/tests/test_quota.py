"""
InkFlow Automated Tests: Quota Engine and Lazy Weekly Reset Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the lazy weekly quota reset and enforcement mechanisms
prescribed in docs/backend.md Section 5:
1. `calculate_next_monday_utc`:
   - Validates that Monday 00:00:00 UTC boundaries are calculated correctly regardless
     of which day of the week the calculation is performed.
2. Word Counting Accuracy (`count_words`):
   - Verifies accurate word count calculation against punctuation, whitespace, and hyphens.
3. Contract Function `enforce_and_reset_quota`:
   - Directly verifies the specification function defined in backend.md Section 5.
4. Free Tier 2,500 Word Limit Enforcement:
   - Verifies that requests within 2,500 words succeed.
   - Verifies that exceeding 2,500 words raises `QuotaExceededException` (HTTP 403 QUOTA_EXCEEDED).
5. Pro Tier Exemption:
   - Verifies that Pro tier accounts bypass the 2,500 limit unconditionally.
6. In-flight Lazy Reset:
   - Verifies that when a user whose reset date has passed makes a new request,
     their word count resets to 0 before applying the new words.
================================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.quota import (
    calculate_next_monday_utc,
    count_words,
    enforce_and_reset_quota,
    check_and_apply_quota,
    QuotaExceededException,
)


def test_calculate_next_monday_utc_from_various_days():
    """
    Tests calculation of the next Monday 00:00:00 UTC boundary from different days of the week.
    """
    # Case 1: Reference time is Tuesday (2026-10-13 14:30:00 UTC)
    tuesday = datetime(2026, 10, 13, 14, 30, 0, tzinfo=timezone.utc)
    next_mon = calculate_next_monday_utc(tuesday)
    assert next_mon.weekday() == 0  # Monday
    assert next_mon.hour == 0 and next_mon.minute == 0 and next_mon.second == 0
    assert next_mon == datetime(2026, 10, 19, 0, 0, 0, tzinfo=timezone.utc)

    # Case 2: Reference time is Sunday (2026-10-18 23:59:59 UTC)
    sunday = datetime(2026, 10, 18, 23, 59, 59, tzinfo=timezone.utc)
    next_mon_from_sun = calculate_next_monday_utc(sunday)
    assert next_mon_from_sun == datetime(2026, 10, 19, 0, 0, 0, tzinfo=timezone.utc)

    # Case 3: Reference time is Monday morning (2026-10-19 09:00:00 UTC)
    monday_morning = datetime(2026, 10, 19, 9, 0, 0, tzinfo=timezone.utc)
    next_mon_from_mon = calculate_next_monday_utc(monday_morning)
    assert next_mon_from_mon == datetime(2026, 10, 26, 0, 0, 0, tzinfo=timezone.utc)


def test_count_words_accuracy():
    """
    Verifies word count computation on varied inputs.
    """
    assert count_words("") == 0
    assert count_words("   \n\t  ") == 0
    assert count_words("Hello world") == 2
    assert count_words("One, two, three — four; five!") == 5
    assert count_words("Hyphenated words-like-this are split into components") == 8


def test_enforce_and_reset_quota_spec_function():
    """
    Verifies the standalone enforce_and_reset_quota function from backend.md Section 5.
    """
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # 1. Under quota free user
    user = {
        "tier": "free",
        "wordsUsedThisWeek": 4600,
        "weeklyWordLimit": 5000,
        "lastWeekReset": start_of_week,
    }
    updated_user, allowed, err = enforce_and_reset_quota(user, 300)
    assert allowed is True
    assert err is None

    # 2. Over quota free user
    updated_user, allowed, err = enforce_and_reset_quota(user, 600)
    assert allowed is False
    assert "Weekly limit reached" in err
    assert "Upgrade to Pro" in err

    # 3. Pro user bypass
    pro_user = {
        "tier": "pro",
        "wordsUsedThisWeek": 10000,
        "lastWeekReset": start_of_week,
    }
    updated_pro, allowed_pro, err_pro = enforce_and_reset_quota(pro_user, 5000)
    assert allowed_pro is True
    assert err_pro is None

    # 4. In-flight reset on stale user (lastWeekReset 2 weeks ago)
    stale_user = {
        "tier": "free",
        "wordsUsedThisWeek": 4900,
        "weeklyWordLimit": 5000,
        "lastWeekReset": start_of_week - timedelta(days=14),
    }
    updated_stale, allowed_stale, err_stale = enforce_and_reset_quota(stale_user, 200)
    assert allowed_stale is True
    assert updated_stale["wordsUsedThisWeek"] == 0
    assert updated_stale["lastWeekReset"] == start_of_week


@pytest.mark.asyncio
async def test_free_tier_within_quota_succeeds():
    """
    Verifies that a Free tier user with available quota can consume words normally.
    """
    user_id = str(ObjectId())
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    mock_user = {
        "_id": ObjectId(user_id),
        "tier": "free",
        "wordsUsedThisWeek": 4000,
        "weeklyWordLimit": 5000,
        "lastWeekReset": start_of_week,
    }

    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=mock_user)
    mock_col.update_one = AsyncMock()

    with patch("app.services.quota.get_users_collection", return_value=mock_col):
        sample_text = "word " * 300
        user, consumed, remaining = await check_and_apply_quota(user_id, sample_text)

        assert consumed == 300
        assert user["wordsUsedThisWeek"] == 4300
        assert remaining == 700  # 5000 - 4300
        mock_col.update_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_free_tier_exceeding_quota_raises_exception():
    """
    Verifies that when a Free tier user attempts to exceed 5,000 words,
    QuotaExceededException (HTTP 403 Forbidden with QUOTA_EXCEEDED) is raised.
    """
    user_id = str(ObjectId())
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    mock_user = {
        "_id": ObjectId(user_id),
        "tier": "free",
        "wordsUsedThisWeek": 4900,
        "weeklyWordLimit": 5000,
        "lastWeekReset": start_of_week,
    }

    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=mock_user)
    mock_col.update_one = AsyncMock()

    with patch("app.services.quota.get_users_collection", return_value=mock_col):
        # 150 words incoming pushes total to 5,050 > 5,000
        sample_text = "word " * 150
        with pytest.raises(QuotaExceededException) as exc_info:
            await check_and_apply_quota(user_id, sample_text)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["status"] == "QUOTA_EXCEEDED"
        mock_col.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_pro_tier_bypasses_quota_limit():
    """
    Verifies that Pro tier users can consume words without restriction.
    """
    user_id = str(ObjectId())
    now = datetime.now(timezone.utc)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    mock_user = {
        "_id": ObjectId(user_id),
        "tier": "pro",
        "wordsUsedThisWeek": 10000,
        "lastWeekReset": start_of_week,
    }

    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=mock_user)
    mock_col.update_one = AsyncMock()

    with patch("app.services.quota.get_users_collection", return_value=mock_col):
        sample_text = "word " * 1000
        user, consumed, remaining = await check_and_apply_quota(user_id, sample_text)

        assert consumed == 1000
        assert user["wordsUsedThisWeek"] == 11000
        assert remaining == 999999
        mock_col.update_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_lazy_reset_triggered_when_overdue():
    """
    Verifies that when current time is past start_of_week, wordsUsedThisWeek
    is automatically reset to 0 in-flight before deducting new words.
    """
    user_id = str(ObjectId())
    past_reset = datetime.now(timezone.utc) - timedelta(days=14)
    mock_user = {
        "_id": ObjectId(user_id),
        "tier": "free",
        "wordsUsedThisWeek": 4950,
        "weeklyWordLimit": 5000,
        "lastWeekReset": past_reset,
    }

    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=mock_user)
    mock_col.update_one = AsyncMock()

    with patch("app.services.quota.get_users_collection", return_value=mock_col):
        sample_text = "word " * 100
        user, consumed, remaining = await check_and_apply_quota(user_id, sample_text)

        assert consumed == 100
        assert user["wordsUsedThisWeek"] == 100
        assert remaining == 4900
        mock_col.update_one.assert_awaited_once()
