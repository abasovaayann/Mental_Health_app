"""
evaluate_model.py — generate evaluation artefacts for the wellness model.

Produces:
  charts/fig_5_3_confusion_matrix.png       — out-of-fold confusion matrix
  charts/fig_5_4_feature_importance.png     — RF feature importance bar chart
  charts/table_5_1_model_comparison.png     — Logistic Regression / Naive Bayes / RF comparison
  charts/model_comparison.csv               — same comparison as CSV

Loads the saved model from artifacts/wellness_model.pkl and the two survey CSVs.
All metrics are reported via 5-fold stratified cross-validation on the same
dataset the model was trained on.
"""

from __future__ import annotations

import pathlib
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
ART = ROOT / "artifacts"
CHARTS = ROOT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)


# ── Encoding (matches the trained model's 14-column schema) ───────────────────
FREQ_MAP = {"never": 1, "rarely": 2, "sometimes": 3, "often": 4, "always": 5}
MORNING_MAP = {
    "very sad": 1, "sad": 2, "neutral": 3, "positive": 4, "energized": 5,
    "very negative": 1, "negative": 2, "very positive": 5,
}
SUPPORT_MAP = {
    "not at all": 1, "slightly": 2, "moderately": 3, "very": 4, "extremely": 5,
}
SLEEP_NORM = {
    "less than 5 hours": "Less than 5 hours",
    "5-6 hours": "5-6 hours",
    "7-8 hours": "7-8 hours",
    "more than 8 hours": "More than 8 hours",
}
SLEEP_COLS = [
    "Sleep Duration_5-6 hours",
    "Sleep Duration_7-8 hours",
    "Sleep Duration_Less than 5 hours",
    "Sleep Duration_More than 8 hours",
    "Sleep Duration_Others",
]
FEATURE_COLS = [
    "Academic Pressure", "Study Satisfaction", "Work/Study Hours",
    "Financial Stress", "Energy Level", "Morning Mood",
    "Emotional Low", "Anxiety Level", "Social Support",
] + SLEEP_COLS

EN_LABEL_MAP = {"very poor": 1, "poor": 1, "neutral": 0, "good": 0, "very good": 0}


def tr_label(val: object) -> int:
    try:
        return 1 if int(val) <= 2 else 0
    except (ValueError, TypeError):
        return 0


def build_row(sleep, academic, motivation, concentration, financial, energy,
              morning_mood, emotional_low, anxiety, social_support) -> dict:
    ap = FREQ_MAP.get(str(academic).strip().lower(), 3)
    sm = int(motivation) if str(motivation).isdigit() else FREQ_MAP.get(str(motivation).strip().lower(), 3)
    cd = FREQ_MAP.get(str(concentration).strip().lower(), 3)
    fs = int(financial) if str(financial).isdigit() else FREQ_MAP.get(str(financial).strip().lower(), 3)
    el = int(energy) if str(energy).isdigit() else FREQ_MAP.get(str(energy).strip().lower(), 3)
    mm = MORNING_MAP.get(str(morning_mood).strip().lower(), 3)
    emo = FREQ_MAP.get(str(emotional_low).strip().lower(), 3)
    anx = FREQ_MAP.get(str(anxiety).strip().lower(), 3)
    ss = SUPPORT_MAP.get(str(social_support).strip().lower(), 3)

    sleep_cat = SLEEP_NORM.get(str(sleep).strip().lower(), "Others")
    row: dict = {
        "Academic Pressure": ap,
        "Study Satisfaction": sm,
        "Work/Study Hours": cd,
        "Financial Stress": fs,
        "Energy Level": el,
        "Morning Mood": mm,
        "Emotional Low": emo,
        "Anxiety Level": anx,
        "Social Support": ss,
    }
    for col in SLEEP_COLS:
        row[col] = 1 if sleep_cat == col.replace("Sleep Duration_", "") else 0
    return row


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    en = pd.read_csv(DATA / "survey_en.csv")
    tr = pd.read_csv(DATA / "survey_tr.csv")
    rows, labels = [], []
    for _, r in en.iterrows():
        rows.append(build_row(
            r.sleep, r.academic_pressure, r.study_motivation, r.concentration,
            r.financial_stress, r.energy, r.morning_mood, r.emotional_low,
            r.anxiety, r.social_support,
        ))
        labels.append(EN_LABEL_MAP.get(str(r.wellbeing).strip().lower(), 0))
    for _, r in tr.iterrows():
        rows.append(build_row(
            r.sleep, r.academic_pressure, r.study_motivation, r.concentration,
            r.financial_stress, r.energy, r.morning_mood, r.emotional_low,
            r.anxiety, r.social_support,
        ))
        labels.append(tr_label(r.wellbeing))
    return pd.DataFrame(rows, columns=FEATURE_COLS), pd.Series(labels, name="at_risk")


def main() -> None:
    X, y = load_dataset()
    n_at_risk = int(y.sum())
    n_not = int((y == 0).sum())
    print(f"Dataset: {len(X)} samples ({n_at_risk} at-risk, {n_not} not at-risk)")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    rf_pipeline = joblib.load(ART / "wellness_model.pkl")

    # ── Figure 5.3 — Confusion matrix (out-of-fold predictions) ───────────────
    print("\n[1/3] Generating confusion matrix...")
    y_pred = cross_val_predict(rf_pipeline, X, y, cv=cv)
    cm = confusion_matrix(y, y_pred)

    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(cm, display_labels=["Not at risk", "At risk"])
    disp.plot(ax=ax, cmap="Blues", colorbar=True, values_format="d")
    ax.set_title("Figure 5.3 — Confusion Matrix (Random Forest, 5-fold CV)")
    plt.tight_layout()
    fig.savefig(CHARTS / "fig_5_3_confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: charts/fig_5_3_confusion_matrix.png")
    print(classification_report(y, y_pred, target_names=["Not at risk", "At risk"]))

    # ── Figure 5.4 — Feature importance bar chart ─────────────────────────────
    print("[2/3] Generating feature importance chart...")
    clf = rf_pipeline.named_steps["clf"]
    importances = pd.Series(clf.feature_importances_, index=FEATURE_COLS).sort_values()

    fig, ax = plt.subplots(figsize=(9, 6))
    importances.plot.barh(ax=ax, color="#4f46e5", edgecolor="#312e81")
    ax.set_title("Figure 5.4 — Feature Importance (Random Forest)")
    ax.set_xlabel("Importance")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    for i, v in enumerate(importances.values):
        ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=8)
    plt.tight_layout()
    fig.savefig(CHARTS / "fig_5_4_feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: charts/fig_5_4_feature_importance.png")

    # ── Table 5.1 — Baseline comparison ───────────────────────────────────────
    print("\n[3/3] Running baseline comparison (LR / NB / RF)...")
    candidates = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=0.5, solver="lbfgs", max_iter=1000,
                class_weight="balanced", random_state=42,
            )),
        ]),
        "Naive Bayes (Gaussian)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GaussianNB()),
        ]),
        "Random Forest (saved)": rf_pipeline,
    }

    rows = []
    for name, model in candidates.items():
        acc = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
        prec = cross_val_score(model, X, y, cv=cv, scoring="precision")
        rec = cross_val_score(model, X, y, cv=cv, scoring="recall")
        f1 = cross_val_score(model, X, y, cv=cv, scoring="f1")
        rows.append({
            "Model": name,
            "Accuracy": f"{acc.mean():.3f} ± {acc.std():.3f}",
            "Precision": f"{prec.mean():.3f} ± {prec.std():.3f}",
            "Recall": f"{rec.mean():.3f} ± {rec.std():.3f}",
            "F1": f"{f1.mean():.3f} ± {f1.std():.3f}",
        })

    df = pd.DataFrame(rows)
    print()
    print(df.to_string(index=False))
    df.to_csv(CHARTS / "model_comparison.csv", index=False)
    print(f"\nSaved: charts/model_comparison.csv")

    # Save the same table as a PNG (handy for the thesis)
    fig, ax = plt.subplots(figsize=(10, 2.4))
    ax.axis("off")
    tbl = ax.table(
        cellText=df.values, colLabels=df.columns,
        cellLoc="center", loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.7)
    for col_idx in range(len(df.columns)):
        header = tbl[(0, col_idx)]
        header.set_facecolor("#4f46e5")
        header.set_text_props(color="white", weight="bold")
    ax.set_title(
        "Table 5.1 — Model Comparison (5-fold cross-validation)",
        pad=12, fontsize=12,
    )
    plt.tight_layout()
    fig.savefig(CHARTS / "table_5_1_model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: charts/table_5_1_model_comparison.png")

    print(f"\nAll outputs written to: {CHARTS}")


if __name__ == "__main__":
    main()
