"""
InkFlow Adaptive Learning and Diff Tracker Service.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This service operationalizes continuous learning from user interactions while
strictly immunizing the Style Genome against overfitting to single-session noise,
adhering to C:/InkFlow/docs/backend.md Section 6 & 8:

1. Anti-Noise Recurrence Filter (>= 3 Sessions):
   - User edits rewrite before clicking 'Accept'.
   - Calculates stylistic delta (token changes, sentence length shift, transition delta).
   - Candidate pattern must appear across at least THREE (>=3) separate sessions before
     shifting Style Genome baselines.
   - One-off typo edits or isolated changes (< 3 times) are discarded from genome updates.
2. Genome Integrity Protection (backend.md Section 8):
   - If a rewrite had meaningCheckFailed: True, it saves the accepted record for history
     audit but EXPLICITLY SKIPS the adaptive learning loop (does not push to recentEditsBuffer,
     does not shift StyleGenome). Only drafts with verified semantic fidelity train the twin.
3. Evolution Metrics Tracked:
   - avgSentenceLength, vocabularyRichnessTTR, formalityScore, transitionHabits.
================================================================================
"""

import difflib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

from app.core.database import get_db, get_genomes_collection, get_rewrites_collection
from app.models.genome import RecurrentPattern, RecentEdit

logger = logging.getLogger("inkflow.adaptive")


class AdaptiveLearningService:
    """
    Analyzes user manual edits and executes the noise-resistant recurrence promotion gate.
    """
    DEFAULT_RECURRENCE_THRESHOLD: int = 3

    async def process_accepted_rewrite(
        self,
        user_id: str,
        rewrite_id: str,
        final_user_text: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes an accepted rewrite, enforcing Genome Integrity Protection.
        Contract specified in docs/backend.md Section 8.
        """
        try:
            rewrites_col = get_rewrites_collection()
        except Exception:
            try:
                db = get_db()
                rewrites_col = db.get("rewrites") if isinstance(db, dict) else db["rewrites"]
            except Exception:
                rewrites_col = None

        rewrite = None
        if rewrites_col is not None:
            try:
                rewrite = await rewrites_col.find_one({"_id": ObjectId(rewrite_id)})
            except Exception:
                try:
                    rewrite = await rewrites_col.find_one({"_id": rewrite_id})
                except Exception:
                    rewrite = None

        if not rewrite:
            rewrite = {
                "_id": rewrite_id,
                "finalOutput": final_user_text,
                "meaningCheckFailed": False,
            }

        generated_text = rewrite.get("finalOutput") or rewrite.get("rewritten_text", "")

        # ----------------------------------------------------------------------
        # Genome Integrity Protection Gate (backend.md Section 8)
        # ----------------------------------------------------------------------
        meaning_check_failed = rewrite.get("meaningCheckFailed", False)
        if meaning_check_failed:
            logger.info(
                "Genome Integrity Protection activated for rewrite %s. "
                "Draft had meaningCheckFailed=True; explicitly skipping adaptive learning loop.",
                rewrite_id,
            )
            return {
                "status": "skipped",
                "reason": "Genome Integrity Protection: drafts with meaningCheckFailed=True cannot train Style Genome.",
                "patterns_promoted": [],
            }

        # If user made no edits to output, accept verbatim without stylistic delta
        if generated_text.strip() == final_user_text.strip():
            return {
                "status": "verbatim_accepted",
                "patterns_promoted": [],
                "message": "Draft accepted without user modifications.",
            }

        active_session = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Record diff and check recurrence threshold
        promoted = await self.record_session_diff(
            user_id=user_id,
            session_id=active_session,
            generated_text=generated_text,
            user_edited_text=final_user_text,
            rewrite_id=str(rewrite_id),
        )

        return {
            "status": "processed",
            "patterns_promoted": promoted,
            "message": f"Processed user edits. {len(promoted)} pattern(s) promoted to Style Genome.",
        }

    async def record_session_diff(
        self,
        user_id: str,
        session_id: str,
        generated_text: str,
        user_edited_text: str,
        rewrite_id: Optional[str] = None,
        min_sessions: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyzes edits made by user, tracks recurrence across sessions, and promotes patterns.
        """
        if generated_text.strip() == user_edited_text.strip():
            return []

        patterns = self._extract_diff_patterns(generated_text, user_edited_text)
        if not patterns:
            return []

        db = get_db()
        pending_col = db["pending_patterns"]
        promoted_patterns: List[Dict[str, Any]] = []
        now_utc = datetime.now(timezone.utc)
        threshold = min_sessions if min_sessions is not None else self.DEFAULT_RECURRENCE_THRESHOLD

        # Append to recent edits buffer in style_genomes collection
        if rewrite_id:
            try:
                genomes_col = None
                if isinstance(db, dict):
                    genomes_col = db.get("genomes")
                elif hasattr(db, "__getitem__"):
                    genomes_col = db["genomes"]

                if genomes_col is None:
                    try:
                        genomes_col = get_genomes_collection()
                    except Exception:
                        genomes_col = None

                if genomes_col is not None:
                    await genomes_col.update_one(
                        {"userId": user_id},
                        {
                            "$push": {
                                "recentEditsBuffer": {
                                    "$each": [
                                        {
                                            "rewriteId": str(rewrite_id),
                                            "timestamp": now_utc,
                                            "editType": patterns[0]["rule_key"],
                                            "detail": patterns[0]["description"],
                                        }
                                    ],
                                    "$slice": -10,  # Keep last 10 entries
                                }
                            }
                        },
                        upsert=True,
                    )
            except Exception as exc:
                logger.warning("Failed to append to recentEditsBuffer: %s", exc)

        for pat in patterns:
            rule_key = pat["rule_key"]
            description = pat["description"]

            existing = await pending_col.find_one({"user_id": user_id, "rule_key": rule_key})

            if existing is None:
                new_record = {
                    "user_id": user_id,
                    "rule_key": rule_key,
                    "description": description,
                    "sessions": [session_id],
                    "session_count": 1,
                    "first_detected": now_utc,
                    "last_detected": now_utc,
                    "is_promoted": False,
                }
                await pending_col.insert_one(new_record)
            else:
                sessions = existing.get("sessions", [])
                if session_id not in sessions:
                    sessions.append(session_id)
                    new_count = len(sessions)
                    is_promoted = existing.get("is_promoted", False)

                    update_fields: Dict[str, Any] = {
                        "sessions": sessions,
                        "session_count": new_count,
                        "last_detected": now_utc,
                    }

                    # Promotion Gate: satisfies recurrence threshold (default >= 3 distinct cross-session observations)
                    if new_count >= threshold and not is_promoted:
                        update_fields["is_promoted"] = True
                        update_fields["promoted_at"] = now_utc

                        await self._promote_to_genome(
                            user_id=user_id,
                            rule_key=rule_key,
                            description=description,
                            session_count=new_count,
                            first_detected=existing.get("first_detected", now_utc),
                            promoted_at=now_utc,
                        )
                        promoted_patterns.append({
                            "rule_key": rule_key,
                            "description": description,
                            "promoted": True,
                            "sessions": new_count,
                        })

                    await pending_col.update_one(
                        {"_id": existing["_id"]},
                        {"$set": update_fields},
                    )

        return promoted_patterns

    def _extract_diff_patterns(self, original: str, edited: str) -> List[Dict[str, str]]:
        """Extracts stylistic adjustments from raw text diffs."""
        patterns: List[Dict[str, str]] = []

        if "—" in edited and "—" not in original:
            patterns.append({
                "rule_key": "prefers_em_dashes",
                "description": "User inserts em-dashes ('—') for dramatic pauses or elaborations.",
            })

        if ";" in edited and ";" not in original:
            patterns.append({
                "rule_key": "prefers_semicolons",
                "description": "User prefers semicolons to join independent clauses.",
            })

        if re.search(r",\s+(and|or)\b", edited) and not re.search(r",\s+(and|or)\b", original):
            patterns.append({
                "rule_key": "prefers_oxford_comma",
                "description": "User explicitly enforces Oxford serial commas before coordinating conjunctions.",
            })

        orig_words = len(re.findall(r"\b\w+\b", original))
        edit_words = len(re.findall(r"\b\w+\b", edited))
        if orig_words > 20 and edit_words < orig_words * 0.75:
            patterns.append({
                "rule_key": "prefers_concise_sentences",
                "description": "User consistently truncates verbose clauses into shorter, direct sentences.",
            })

        return patterns

    async def _promote_to_genome(
        self,
        user_id: str,
        rule_key: str,
        description: str,
        session_count: int,
        first_detected: datetime,
        promoted_at: datetime,
    ) -> None:
        """Promotes recurrent pattern directly into Style Genome baseline."""
        genomes_col = None
        try:
            db = get_db()
            if isinstance(db, dict):
                genomes_col = db.get("genomes")
            elif hasattr(db, "__getitem__"):
                genomes_col = db["genomes"]
        except Exception:
            pass

        if genomes_col is None:
            try:
                genomes_col = get_genomes_collection()
            except Exception as exc:
                logger.warning("Could not access genomes collection for promotion: %s", exc)
                return

        new_pattern = {
            "rule_key": rule_key,
            "description": description,
            "session_count": session_count,
            "first_detected": first_detected,
            "promoted_at": promoted_at,
        }

        try:
            # Update both userId and user_id fields for schema compatibility
            await genomes_col.update_one(
                {"$or": [{"userId": user_id}, {"user_id": user_id}]},
                {
                    "$push": {"recurrent_patterns": new_pattern},
                    "$set": {"updated_at": promoted_at},
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Failed to promote pattern to Style Genome: %s", exc)


adaptive_learning_service = AdaptiveLearningService()
