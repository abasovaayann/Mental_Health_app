"""
Train a Random Forest classifier to predict student depression.

Dataset: Student Depression Dataset (Kaggle – hopesb/student-depression-dataset)
Steps:
    1. Load CSV
    2. Drop noisy / high-cardinality columns (id, City, Profession, Degree)
    3. Label-encode remaining categorical features
    4. Train / test split (80 / 20)
    5. Fit RandomForestClassifier
    6. Evaluate (accuracy + classification report)
    7. Show feature importance
    8. Save model with joblib
"""

import os
import pathlib

import joblib
import matplotlib
matplotlib.use("Agg")                      # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
MODEL_DIR  = SCRIPT_DIR / "artifacts"
MODEL_DIR.mkdir(exist_ok=True)

# Try the Kaggle path first, then fall back to a local cached copy
KAGGLE_PATH = pathlib.Path(
    "/kaggle/input/student-depression-dataset/student_depression_dataset.csv"
)
LOCAL_PATH = pathlib.Path(
    os.path.expanduser(
        "~/.cache/kagglehub/datasets/hopesb/"
        "student-depression-dataset/versions/1/"
        "Student Depression Dataset.csv"
    )
)

CSV_PATH = KAGGLE_PATH if KAGGLE_PATH.exists() else LOCAL_PATH

# ── 1. Load data ─────────────────────────────────────────────────────────────
print(f"Loading data from: {CSV_PATH}")
data = pd.read_csv(CSV_PATH)
print(f"Shape: {data.shape}")

# ── 2. Drop columns ──────────────────────────────────────────────────────────
DROP_COLS = ["id", "City", "Profession", "Degree"]
data.drop(columns=[c for c in DROP_COLS if c in data.columns], inplace=True)

# Drop rows with missing target
data.dropna(subset=["Depression"], inplace=True)

print(f"Shape after cleaning: {data.shape}")
print(f"Columns: {data.columns.tolist()}\n")

# ── 3. Encode categorical features ───────────────────────────────────────────
label_encoders: dict[str, LabelEncoder] = {}
cat_cols = data.select_dtypes(include=["object"]).columns.tolist()

for col in cat_cols:
    le = LabelEncoder()
    data[col] = le.fit_transform(data[col].astype(str))
    label_encoders[col] = le
    print(f"  Encoded '{col}': {list(le.classes_)}")

print()

# ── 4. Train / test split ────────────────────────────────────────────────────
TARGET = "Depression"
X = data.drop(columns=[TARGET])
y = data[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"Train size: {X_train.shape[0]}   Test size: {X_test.shape[0]}\n")

# ── 5. Train Random Forest ───────────────────────────────────────────────────
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1,
)
rf.fit(X_train, y_train)

# ── 6. Evaluate ──────────────────────────────────────────────────────────────
y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"Accuracy: {acc:.4f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred, target_names=["No Depression", "Depression"]))

# ── 7. Feature importance ────────────────────────────────────────────────────
importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]
feature_names = X.columns

print("Feature Importances (descending):")
for rank, idx in enumerate(indices, 1):
    print(f"  {rank:2d}. {feature_names[idx]:<45s} {importances[idx]:.4f}")

# Save a bar chart
plt.figure(figsize=(10, 6))
plt.title("Random Forest – Feature Importance")
plt.barh(
    range(len(indices)),
    importances[indices[::-1]],
    align="center",
)
plt.yticks(range(len(indices)), [feature_names[i] for i in indices[::-1]])
plt.xlabel("Importance")
plt.tight_layout()

chart_path = MODEL_DIR / "feature_importance.png"
plt.savefig(chart_path, dpi=150)
print(f"\nFeature-importance chart saved to: {chart_path}")

# ── 8. Save model & encoders with joblib ─────────────────────────────────────
model_path   = MODEL_DIR / "depression_rf_model.joblib"
encoder_path = MODEL_DIR / "label_encoders.joblib"

joblib.dump(rf, model_path)
joblib.dump(label_encoders, encoder_path)

print(f"Model saved to:    {model_path}")
print(f"Encoders saved to: {encoder_path}")
print("\nDone ✓")
