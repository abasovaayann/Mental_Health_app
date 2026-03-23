"""
Global mapping dictionaries – convert every text-based survey answer
to a numeric value on a consistent 1-5 integer scale.

Each dictionary is intentionally **lowercase-keyed** so lookups are
case-insensitive (callers should ``.lower().strip()`` before lookup).

Scale semantics:
    1 = lowest / least / never / worst
    5 = highest / most / always / best
"""

from __future__ import annotations

# ─── Frequency scale ─────────────────────────────────────────────────────────
#   Never → Rarely → Sometimes → Often → Always / Constantly / Almost always
FREQUENCY_SCALE: dict[str, int] = {
    "never":         1,
    "rarely":        2,
    "sometimes":     3,
    "often":         4,
    "always":        5,
    "constantly":    5,
    "almost always": 5,
}

# ─── Intensity scale ─────────────────────────────────────────────────────────
#   Very low → Low → Moderate → High → Very high
INTENSITY_SCALE: dict[str, int] = {
    "very low":  1,
    "low":       2,
    "moderate":  3,
    "high":      4,
    "very high": 5,
}

# ─── Sentiment / mood scale ──────────────────────────────────────────────────
#   Very negative → Negative → Neutral → Positive → Very positive
#   Also covers the morning-mood wording in our survey
SENTIMENT_SCALE: dict[str, int] = {
    "very negative":            1,
    "negative":                 2,
    "neutral":                  3,
    "positive":                 4,
    "very positive":            5,
    # morning-mood answer text
    "very sad / hopeless":      1,
    "sad":                      2,
    # "neutral" already mapped
    # "positive" already mapped
    "very happy / energized":   5,
}

# ─── Support scale ───────────────────────────────────────────────────────────
#   Not at all → Slightly → Moderately → Very → Extremely
SUPPORT_SCALE: dict[str, int] = {
    "not at all":      1,
    "slightly":        2,
    "moderately":      3,
    "mostly":          4,
    "very":            5,
    "very supported":  5,
    "extremely":       5,
}

# ─── Motivation scale ────────────────────────────────────────────────────────
MOTIVATION_SCALE: dict[str, int] = {
    "not motivated":       1,
    "slightly motivated":  2,
    "neutral":             3,
    "motivated":           4,
    "highly motivated":    5,
}

# ─── Concentration-difficulty scale ──────────────────────────────────────────
#   Higher value → more difficulty (worse concentration)
CONCENTRATION_SCALE: dict[str, int] = {
    "not difficult":        1,
    "slightly difficult":   2,
    "moderately difficult": 3,
    "very difficult":       4,
    "extremely difficult":  5,
}

# ─── Financial-stress scale ──────────────────────────────────────────────────
FINANCIAL_SCALE: dict[str, int] = {
    "none":           1,
    "low":            2,
    "moderate":       3,
    "high":           4,
    "extremely high": 5,
}

# ─── Sleep-duration mapping ──────────────────────────────────────────────────
#   The frontend sends a slider value "1"–"5" as a string.
#   We also accept natural-language descriptions for flexibility.
#   Value = estimated midpoint hours (float) for the RF model.
SLEEP_DURATION_MAP: dict[str, float] = {
    # slider values (stored as strings in DB)
    "1": 3.5,   # Less than 4 hours
    "2": 4.5,   # 4-5 hours
    "3": 6.0,   # 6 hours
    "4": 7.5,   # 7-8 hours
    "5": 9.0,   # More than 8 hours
    # natural-language aliases (Kaggle dataset style)
    "less than 4 hours":  3.5,
    "less than 5 hours":  4.0,
    "4-5 hours":          4.5,
    "5-6 hours":          5.5,
    "6 hours":            6.0,
    "7-8 hours":          7.5,
    "more than 8 hours":  9.0,
}

# ─── Field → scale registry ─────────────────────────────────────────────────
#   Maps each survey field name to the correct mapping dict so that
#   ``encode_survey`` can encode the full response automatically.
#   ``sleep_duration`` is handled separately by ``encode_sleep_duration``.
FIELD_SCALE_REGISTRY: dict[str, dict[str, int]] = {
    "energy_level":              INTENSITY_SCALE,
    "academic_pressure":         FREQUENCY_SCALE,
    "study_motivation":          MOTIVATION_SCALE,
    "concentration_difficulty":  CONCENTRATION_SCALE,
    "morning_mood":              SENTIMENT_SCALE,
    "emotional_low":             FREQUENCY_SCALE,
    "anxiety_level":             FREQUENCY_SCALE,
    "social_support":            SUPPORT_SCALE,
    "financial_stress":          FINANCIAL_SCALE,
}
