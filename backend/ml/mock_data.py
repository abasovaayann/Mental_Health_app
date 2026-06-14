"""
Synthetic survey-response generator used to augment the wellness training set.

Each feature has a small ordinal value pool (ordered from "low distress" to
"high distress"). For a given target class we sample each feature's value
independently from a class-conditional distribution: at-risk samples are
biased toward the high-distress end, not-at-risk toward the low-distress end.

Crucially, *both* distributions assign non-zero probability to *every* value,
so the synthetic samples overlap with the real distribution and the model is
forced to learn the actual decision boundary instead of memorising rules.
"""

from __future__ import annotations

import random
from collections.abc import Iterable

# Each feature's choices, ordered from "low distress" -> "high distress".
# Mock generation samples an index using a class-conditional weight vector,
# then maps it back to the original text value. This keeps the generator and
# the encoder in lock-step: any new value here must also be recognised by
# ``ml.predict._encode_survey``.
FEATURE_CHOICES: dict[str, list[str]] = {
    "sleep_duration": [
        "More than 8 hours",
        "7-8 hours",
        "5-6 hours",
        "Less than 5 hours",
    ],
    "energy_level": ["very high", "high", "moderate", "low", "very low"],
    "academic_pressure": ["never", "rarely", "sometimes", "often", "always"],
    "study_motivation": [
        "highly motivated",
        "motivated",
        "neutral",
        "slightly motivated",
        "not motivated",
    ],
    "concentration_difficulty": [
        "not difficult",
        "slightly difficult",
        "moderately difficult",
        "very difficult",
        "extremely difficult",
    ],
    "morning_mood": ["energized", "positive", "neutral", "sad", "very sad"],
    "emotional_low": ["never", "rarely", "sometimes", "often", "always"],
    "anxiety_level": ["never", "rarely", "sometimes", "often", "always"],
    "social_support": [
        "very supported",
        "mostly",
        "moderately",
        "slightly",
        "not at all",
    ],
    "financial_stress": ["none", "low", "moderate", "high", "extremely high"],
}

# Weight vectors keyed by choice-list length. Index 0 = lowest distress.
_AT_RISK_WEIGHTS: dict[int, list[float]] = {
    5: [0.04, 0.10, 0.21, 0.35, 0.30],
    4: [0.05, 0.15, 0.40, 0.40],
}
_NOT_AT_RISK_WEIGHTS: dict[int, list[float]] = {
    5: [0.28, 0.34, 0.22, 0.11, 0.05],
    4: [0.28, 0.47, 0.20, 0.05],
}


def _weights_for(at_risk: bool, n_choices: int) -> list[float]:
    table = _AT_RISK_WEIGHTS if at_risk else _NOT_AT_RISK_WEIGHTS
    return table[n_choices]


def generate_record(rng: random.Random, at_risk: bool) -> dict[str, str]:
    record: dict[str, str] = {}
    for name, choices in FEATURE_CHOICES.items():
        weights = _weights_for(at_risk, len(choices))
        record[name] = rng.choices(choices, weights=weights, k=1)[0]
    return record


def generate_dataset(
    n_at_risk: int,
    n_not_at_risk: int,
    *,
    random_state: int = 42,
) -> tuple[list[dict[str, str]], list[int]]:
    """Generate ``n_at_risk`` + ``n_not_at_risk`` synthetic survey responses
    from the hand-coded class-conditional weight tables above.

    Returns the raw-answer dicts (text values, matching the encoder's
    accepted vocabulary) plus the binary at-risk labels, both shuffled so a
    plain head-of-dataset slice doesn't get all of one class.
    """
    rng = random.Random(random_state)
    rows: list[dict[str, str]] = []
    labels: list[int] = []

    for _ in range(n_at_risk):
        rows.append(generate_record(rng, at_risk=True))
        labels.append(1)
    for _ in range(n_not_at_risk):
        rows.append(generate_record(rng, at_risk=False))
        labels.append(0)

    combined = list(zip(rows, labels))
    rng.shuffle(combined)
    rows = [item[0] for item in combined]
    labels = [item[1] for item in combined]
    return rows, labels


def generate_empirical_dataset(
    real_rows: list[dict[str, str]],
    real_labels: list[int],
    n_at_risk: int,
    n_not_at_risk: int,
    *,
    random_state: int = 42,
) -> tuple[list[dict[str, str]], list[int]]:
    """Generate mock rows by sampling each feature independently from its
    class-conditional *empirical* distribution observed in the real data.

    This guarantees that every per-feature marginal in the mock set matches
    the real data exactly (per class), so adding mock samples does not pull
    the model toward a distribution that production never sees. The cost
    is that joint dependencies between features are broken — mock rows are
    plausible per-feature but not necessarily per-row.
    """
    rng = random.Random(random_state)

    buckets: dict[int, dict[str, list[str]]] = {0: {}, 1: {}}
    for row, label in zip(real_rows, real_labels):
        bucket = buckets[label]
        for feature in FEATURE_CHOICES.keys():
            value = row.get(feature)
            if value is None or str(value).strip() == "":
                continue
            bucket.setdefault(feature, []).append(str(value).strip())

    rows: list[dict[str, str]] = []
    labels: list[int] = []
    for label, count in [(1, n_at_risk), (0, n_not_at_risk)]:
        bucket = buckets[label]
        for _ in range(count):
            row = {}
            for feature in FEATURE_CHOICES.keys():
                pool = bucket.get(feature)
                if not pool:
                    # Fall back to the rule-based weights for this feature.
                    choices = FEATURE_CHOICES[feature]
                    weights = _weights_for(bool(label), len(choices))
                    row[feature] = rng.choices(choices, weights=weights, k=1)[0]
                else:
                    row[feature] = rng.choice(pool)
            rows.append(row)
            labels.append(label)

    combined = list(zip(rows, labels))
    rng.shuffle(combined)
    return [c[0] for c in combined], [c[1] for c in combined]


def write_csv(
    path,
    rows: Iterable[dict[str, str]],
    labels: Iterable[int],
) -> None:
    """Persist generated rows to a CSV (used for auditability)."""
    import csv

    rows = list(rows)
    labels = list(labels)
    fieldnames = list(FEATURE_CHOICES.keys()) + ["at_risk"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row, label in zip(rows, labels):
            payload = dict(row)
            payload["at_risk"] = label
            writer.writerow(payload)
