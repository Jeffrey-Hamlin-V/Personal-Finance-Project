import time
import os
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    log_loss,
    confusion_matrix
)

# =========================
# CONFIG
# =========================

DATA_FILE = "clean_transactions.csv"
MODEL_OUT = "models/logreg_model.joblib"
RANDOM_STATE = 42

os.makedirs("models", exist_ok=True)

# =========================
# LOAD DATA
# =========================

df = pd.read_csv(DATA_FILE)

X = df["clean_description"].fillna("")
y = df["category"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_STATE,
    stratify=y
)

# =========================
# TF-IDF (LOCKED)
# =========================

tfidf = TfidfVectorizer(
    lowercase=True,
    ngram_range=(1, 2),
    min_df=3,
    max_df=0.9,
    max_features=30000,
    sublinear_tf=True
)

X_train_vec = tfidf.fit_transform(X_train)
X_test_vec = tfidf.transform(X_test)

# =========================
# MODEL
# =========================

model = LogisticRegression(
    multi_class="multinomial",
    solver="lbfgs",
    C=1.0,
    max_iter=1000,
    n_jobs=-1,
    class_weight="balanced"
)

# =========================
# TRAIN
# =========================

start = time.time()
model.fit(X_train_vec, y_train)
train_time = time.time() - start

# =========================
# TEST / EVALUATION
# =========================

start = time.time()
y_pred = model.predict(X_test_vec)
infer_time = time.time() - start

y_proba = model.predict_proba(X_test_vec)

accuracy = accuracy_score(y_test, y_pred)
macro_f1 = f1_score(y_test, y_pred, average="macro")
logloss = log_loss(y_test, y_proba)

print("\n=== LOGISTIC REGRESSION RESULTS ===")
print(f"Train time: {train_time:.2f}s")
print(f"Inference time (test set): {infer_time:.4f}s")
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}")
print(f"Log Loss: {logloss:.4f}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# =========================
# MODEL SIZE
# =========================

joblib.dump({"vectorizer": tfidf, "model": model}, MODEL_OUT)
model_size_mb = os.path.getsize(MODEL_OUT) / (1024 * 1024)

print(f"Model size: {model_size_mb:.2f} MB")
print(f"Model saved to {MODEL_OUT}")
