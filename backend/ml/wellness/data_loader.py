"""
data_loader.py
==============
Query the live database and return labelled training records for model retraining.

Label derivation
----------------
Users who have **both** a completed baseline survey and enough daily check-ins
are included.  Their average ``mood_level`` (0-100 slider) is used as a
behavioural ground-truth label:

    avg_mood  <  MOOD_RISK_THRESHOLD  →  at-risk    (label = 1)
    avg_mood  >= MOOD_RISK_THRESHOLD  →  not at-risk (label = 0)

Default threshold: 40  (tunable via environment variable MOOD_RISK_THRESHOLD).

Usage
-----
    from app.database import SessionLocal
    from ml.wellness.data_loader import get_training_records

    db = SessionLocal()
    records = get_training_records(db)   # list[dict] with encoded features + label
    db.close()
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sqlalchemy import func

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Minimum number of daily check-ins a user must have to be included
MIN_CHECKINS: int = int(os.environ.get("MIN_CHECKINS", "3"))

# avg(mood_level) below this → at-risk label
MOOD_RISK_THRESHOLD: int = int(os.environ.get("MOOD_RISK_THRESHOLD", "40"))


def get_training_records(
    db: "Session",
    *,
    min_checkins: int = MIN_CHECKINS,
    mood_threshold: int = MOOD_RISK_THRESHOLD,
) -> list[dict]:
    """
    Return a list of encoded feature dicts with a binary ``label`` key,
    suitable for passing directly to ``WellnessRetrainer.retrain()``.

    Parameters
    ----------
    db : sqlalchemy Session
    min_checkins : int
        Minimum daily check-ins a user must have to be included.
    mood_threshold : int
        Average mood_level below which a user is labelled at-risk (1).

    Returns
    -------
    list[dict]
        Each dict has keys matching ``ALL_FEATURES`` plus ``"label"`` (0/1).
        Rows that fail encoding are silently dropped.
    """
    # Import here to avoid circular imports at module load time
    from app.models.survey import BaselineSurvey, DailyCheckin
    from ml.wellness.encoders import encode_survey

    # ── Aggregate check-in stats per user ─────────────────────────────────────
    checkin_stats = (
        db.query(
            DailyCheckin.user_id,
            func.count(DailyCheckin.id).label("n_checkins"),
            func.avg(DailyCheckin.mood_level).label("avg_mood"),
        )
        .group_by(DailyCheckin.user_id)
        .having(func.count(DailyCheckin.id) >= min_checkins)
        .subquery()
    )

    # ── Join with baseline surveys ────────────────────────────────────────────
    rows = (
        db.query(BaselineSurvey, checkin_stats.c.avg_mood)
        .join(checkin_stats, BaselineSurvey.user_id == checkin_stats.c.user_id)
        .all()
    )

    records: list[dict] = []

    for survey, avg_mood in rows:
        raw_answers = {
            "sleep_duration":           survey.sleep_duration,
            "energy_level":             survey.energy_level,
            "academic_pressure":        survey.academic_pressure,
            "study_motivation":         survey.study_motivation,
            "concentration_difficulty": survey.concentration_difficulty,
            "morning_mood":             survey.morning_mood,
            "emotional_low":            survey.emotional_low,
            "anxiety_level":            survey.anxiety_level,
            "social_support":           survey.social_support,
            "financial_stress":         survey.financial_stress,
        }

        try:
            encoded = encode_survey(raw_answers)
        except (KeyError, ValueError):
            # Unknown answer value – skip this row
            continue

        label = 1 if float(avg_mood) < mood_threshold else 0
        encoded["label"] = label
        records.append(encoded)

    return records


def count_eligible_users(
    db: "Session",
    *,
    min_checkins: int = MIN_CHECKINS,
) -> dict:
    """
    Return a summary of how many users are eligible for retraining.

    Useful for the /training-status API endpoint.
    """
    from app.models.survey import BaselineSurvey, DailyCheckin
    from ml.wellness.retrainer import MIN_SAMPLES

    total_with_survey = db.query(BaselineSurvey).count()

    checkin_counts = (
        db.query(
            DailyCheckin.user_id,
            func.count(DailyCheckin.id).label("n"),
        )
        .group_by(DailyCheckin.user_id)
        .having(func.count(DailyCheckin.id) >= min_checkins)
        .subquery()
    )

    eligible = (
        db.query(func.count())
        .select_from(BaselineSurvey)
        .join(checkin_counts, BaselineSurvey.user_id == checkin_counts.c.user_id)
        .scalar()
    ) or 0

    return {
        "total_users_with_survey":   total_with_survey,
        "eligible_for_training":     eligible,
        "min_checkins_required":     min_checkins,
        "min_samples_for_retrain":   MIN_SAMPLES,
        "ready_to_retrain":          eligible >= MIN_SAMPLES,
        "samples_needed":            max(0, MIN_SAMPLES - eligible),
    }
