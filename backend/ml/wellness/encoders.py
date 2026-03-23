"""
Encoding functions – convert raw text survey answers to numeric values.

Public API
----------
encode_answer(field, value)        → int   (1-5)
encode_sleep_duration(value)       → float (estimated hours)
encode_survey(raw_answers: dict)   → dict  (all fields encoded)
"""

from __future__ import annotations

from .mappings import FIELD_SCALE_REGISTRY, SLEEP_DURATION_MAP


def encode_answer(field: str, value: str) -> int:
    """
    Encode a single categorical answer to its 1-5 numeric value.

    Parameters
    ----------
    field : str
        Survey field name, e.g. ``"academic_pressure"``.
    value : str
        Raw text answer, e.g. ``"Often"``.

    Returns
    -------
    int
        Encoded value (1-5).

    Raises
    ------
    KeyError
        If *field* has no registered scale or *value* is not in that scale.

    Examples
    --------
    >>> encode_answer("academic_pressure", "Often")
    4
    >>> encode_answer("energy_level", "Very low")
    1
    """
    scale = FIELD_SCALE_REGISTRY.get(field)
    if scale is None:
        raise KeyError(f"No encoding scale registered for field '{field}'")

    key = value.strip().lower()
    if key not in scale:
        raise KeyError(
            f"Unknown value '{value}' for field '{field}'. "
            f"Valid options: {list(scale.keys())}"
        )
    return scale[key]


def encode_sleep_duration(value: str) -> float:
    """
    Encode a sleep-duration answer to estimated hours (float).

    Accepts both the frontend slider strings (``"1"``–``"5"``) and
    natural-language descriptions (``"7-8 hours"``).

    Parameters
    ----------
    value : str
        Raw sleep-duration answer.

    Returns
    -------
    float
        Estimated sleep hours.

    Examples
    --------
    >>> encode_sleep_duration("4")
    7.5
    >>> encode_sleep_duration("Less than 5 hours")
    4.0
    """
    key = value.strip().lower()
    if key not in SLEEP_DURATION_MAP:
        raise KeyError(
            f"Unknown sleep duration '{value}'. "
            f"Valid options: {list(SLEEP_DURATION_MAP.keys())}"
        )
    return SLEEP_DURATION_MAP[key]


def encode_survey(raw_answers: dict[str, str]) -> dict[str, int | float]:
    """
    Encode an entire baseline-survey response dict.

    Parameters
    ----------
    raw_answers : dict[str, str]
        Keys must match the survey field names stored in the DB:
        ``sleep_duration``, ``energy_level``, ``academic_pressure``,
        ``study_motivation``, ``concentration_difficulty``,
        ``morning_mood``, ``emotional_low``, ``anxiety_level``,
        ``social_support``, ``financial_stress``.

    Returns
    -------
    dict[str, int | float]
        Same keys, with numeric values.

    Examples
    --------
    >>> raw = {
    ...     "sleep_duration": "4",
    ...     "energy_level": "Moderate",
    ...     "academic_pressure": "Often",
    ...     "study_motivation": "Motivated",
    ...     "concentration_difficulty": "Moderately difficult",
    ...     "morning_mood": "Neutral",
    ...     "emotional_low": "Sometimes",
    ...     "anxiety_level": "Sometimes",
    ...     "social_support": "Moderately",
    ...     "financial_stress": "Moderate",
    ... }
    >>> encoded = encode_survey(raw)
    >>> encoded["sleep_duration"]
    7.5
    >>> encoded["academic_pressure"]
    4
    """
    encoded: dict[str, int | float] = {}

    for field, value in raw_answers.items():
        if field == "sleep_duration":
            encoded[field] = encode_sleep_duration(value)
        else:
            encoded[field] = encode_answer(field, value)

    return encoded
