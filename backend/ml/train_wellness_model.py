import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# ── Locate dataset ───────────────────────────────────────────────────────────
KAGGLE_PATH = "/kaggle/input/student-depression-dataset/student_depression_dataset.csv"
LOCAL_PATH = os.path.expanduser(
    "~/.cache/kagglehub/datasets/hopesb/"
    "student-depression-dataset/versions/1/"
    "Student Depression Dataset.csv"
)
CSV_PATH = KAGGLE_PATH if os.path.exists(KAGGLE_PATH) else LOCAL_PATH

# Load dataset
print(f"Loading data from: {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
print(f"Original shape: {df.shape}")

# Keep only the columns your app can match
df = df[
    [
        "Sleep Duration",
        "Academic Pressure",
        "Study Satisfaction",
        "Work/Study Hours",
        "Financial Stress",
        "Depression",
    ]
].copy()

print(f"Filtered shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}\n")

# Separate features and target
X = df.drop("Depression", axis=1)
y = df["Depression"]

# Encode categorical columns
X = pd.get_dummies(X, drop_first=False)

print(f"Features after encoding: {X.columns.tolist()}")
print(f"Feature matrix shape: {X.shape}\n")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train size: {X_train.shape[0]}   Test size: {X_test.shape[0]}\n")

# Train model
model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# Save model
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
os.makedirs(SAVE_DIR, exist_ok=True)

model_path = os.path.join(SAVE_DIR, "wellness_model.pkl")
columns_path = os.path.join(SAVE_DIR, "model_columns.pkl")

joblib.dump(model, model_path)
joblib.dump(X.columns.tolist(), columns_path)

print(f"\nModel saved to:   {model_path}")
print(f"Columns saved to: {columns_path}")
print("Model and columns saved successfully.")
