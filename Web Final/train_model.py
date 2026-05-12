"""
TerraAI - Model Training Script
Trains an ensemble (RandomForest + CatBoost) crop recommendation model
and saves crop_model.pkl + label_encoder.pkl to the models/ directory.
Run once before starting the Flask app: python train_model.py
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ── Try importing CatBoost; fall back gracefully ──────────────────────────────
try:
    from catboost import CatBoostClassifier
    USE_CATBOOST = True
except ImportError:
    print("[WARN] CatBoost not installed – using RandomForest-only ensemble.")
    USE_CATBOOST = False

# ── Synthetic dataset (22 crops × 100 samples each) ──────────────────────────
CROPS = [
    "Rice", "Maize", "Chickpea", "KidneyBeans", "PigeonPeas",
    "MothBeans", "MungBean", "Blackgram", "Lentil", "Pomegranate",
    "Banana", "Mango", "Grapes", "Watermelon", "Muskmelon",
    "Apple", "Orange", "Papaya", "CoconutTree", "Cotton",
    "Jute", "Coffee",
]

# Ideal soil/climate ranges per crop  [N, P, K, temp, humidity, ph, rainfall]
CROP_PROFILES = {
    "Rice":         [80, 40, 40, 25, 82, 6.5, 200],
    "Maize":        [80, 40, 20, 22, 65, 6.0, 85],
    "Chickpea":     [40, 67, 79, 18, 16, 7.0, 80],
    "KidneyBeans":  [20, 67, 20, 20, 22, 5.7, 105],
    "PigeonPeas":   [20, 67, 20, 27, 48, 5.8, 150],
    "MothBeans":    [20, 40, 20, 28, 53, 6.9, 51],
    "MungBean":     [20, 40, 20, 29, 85, 6.7, 48],
    "Blackgram":    [40, 67, 19, 30, 65, 7.1, 67],
    "Lentil":       [18, 68, 19, 24, 65, 6.9, 45],
    "Pomegranate":  [18, 18, 40, 21, 90, 6.5, 107],
    "Banana":       [100, 82, 50, 27, 80, 5.8, 105],
    "Mango":        [20, 27, 30, 31, 50, 5.7, 95],
    "Grapes":       [23, 132, 200, 24, 82, 6.0, 70],
    "Watermelon":   [99, 17, 50, 25, 85, 6.5, 50],
    "Muskmelon":    [100, 17, 50, 28, 92, 6.3, 25],
    "Apple":        [21, 134, 199, 22, 92, 5.9, 113],
    "Orange":       [20, 16, 10, 23, 92, 7.0, 110],
    "Papaya":       [49, 59, 50, 34, 92, 6.7, 143],
    "CoconutTree":  [22, 16, 30, 27, 94, 5.9, 175],
    "Cotton":       [117, 46, 19, 24, 80, 6.9, 80],
    "Jute":         [78, 46, 40, 25, 80, 6.5, 175],
    "Coffee":       [101, 28, 29, 25, 58, 6.8, 158],
}

SAMPLES_PER_CROP = 120
NOISE = 0.12   # ±12 % Gaussian noise

rng = np.random.default_rng(42)

rows, labels = [], []
for crop, profile in CROP_PROFILES.items():
    base = np.array(profile, dtype=float)
    for _ in range(SAMPLES_PER_CROP):
        noise = rng.normal(0, NOISE, size=len(base))
        sample = base * (1 + noise)
        # clamp to realistic ranges
        sample[0] = np.clip(sample[0], 0, 140)   # N
        sample[1] = np.clip(sample[1], 5, 145)   # P
        sample[2] = np.clip(sample[2], 5, 205)   # K
        sample[3] = np.clip(sample[3], 8, 44)    # temp
        sample[4] = np.clip(sample[4], 14, 100)  # humidity
        sample[5] = np.clip(sample[5], 3.5, 9.5) # ph
        sample[6] = np.clip(sample[6], 20, 300)  # rainfall
        rows.append(sample)
        labels.append(crop)

df = pd.DataFrame(rows, columns=["N", "P", "K", "temperature", "humidity", "ph", "rainfall"])
df["label"] = labels

print(f"[INFO] Dataset: {len(df)} samples, {df['label'].nunique()} crops")

# ── Encode labels ─────────────────────────────────────────────────────────────
le = LabelEncoder()
y = le.fit_transform(df["label"])
X = df.drop("label", axis=1).values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Build estimators ──────────────────────────────────────────────────────────
rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    random_state=42,
    n_jobs=-1,
)

if USE_CATBOOST:
    cb = CatBoostClassifier(
        iterations=300,
        learning_rate=0.05,
        depth=6,
        verbose=0,
        random_seed=42,
    )
    model = VotingClassifier(
        estimators=[("rf", rf), ("cb", cb)],
        voting="soft",
        weights=[1, 1],
    )
    print("[INFO] Training RandomForest + CatBoost ensemble …")
else:
    # Double-weight RF as a simple ensemble stand-in
    rf2 = RandomForestClassifier(
        n_estimators=300, max_depth=None, random_state=99, n_jobs=-1
    )
    model = VotingClassifier(
        estimators=[("rf1", rf), ("rf2", rf2)],
        voting="soft",
    )
    print("[INFO] Training dual-RandomForest ensemble …")

model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"[INFO] Test accuracy: {acc * 100:.2f}%")

# ── Save artefacts ────────────────────────────────────────────────────────────
os.makedirs("models", exist_ok=True)

with open("models/crop_model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("models/label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

print("[INFO] Saved  models/crop_model.pkl")
print("[INFO] Saved  models/label_encoder.pkl")
print("[DONE] Training complete. You can now run: python app.py")
