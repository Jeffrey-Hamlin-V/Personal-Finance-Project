import re
import pandas as pd
from datetime import datetime

# =========================
# CONFIG
# =========================

INPUT_FILE = "Data5.csv"
OUTPUT_FILE = "Test5.csv"

# Tokens commonly found in bank statements that add no semantic value
NOISE_TOKENS = {
    "pos", "visa", "mastercard", "debit", "credit", "ecom",
    "auth", "authcode", "approved", "card", "payment",
    "transaction", "purchase", "terminal", "term",
    "intl", "fee", "fx", "exchange",
    "recurring", "subscription", "online", "ecommerce",
    "ref", "trace", "seq", "batch", "settled", "pending",
    "contactless", "chip", "pin", "tap"
}

# Remove numbers longer than this (IDs, auth codes, etc.)
LONG_NUMBER_LEN = 4

# =========================
# TEXT CLEANING
# =========================

def normalize_text(text: str) -> str:
    """
    Clean and normalize noisy bank transaction descriptions.
    """
    if pd.isna(text):
        return ""

    text = text.lower()

    # Replace separators with spaces
    text = re.sub(r"[\-\_\*\@\.\|#:/;]", " ", text)

    # Remove long numeric tokens (IDs, references)
    text = re.sub(rf"\b\d{{{LONG_NUMBER_LEN},}}\b", " ", text)

    # Remove alphanumeric codes like AUTH928374
    text = re.sub(r"\b[a-z]*\d+[a-z\d]*\b", " ", text)

    tokens = []
    for token in text.split():
        if token in NOISE_TOKENS:
            continue
        if len(token) <= 1:
            continue
        tokens.append(token)

    return " ".join(tokens)

# =========================
# TIME FEATURES
# =========================

def derive_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek  # Monday=0
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    df["is_night"] = df["hour_of_day"].between(0, 5)

    return df

# =========================
# MAIN PIPELINE
# =========================

def clean_dataset(input_file: str) -> pd.DataFrame:
    df = pd.read_csv(input_file)

    # Normalize description text
    df["clean_description"] = df["description"].apply(normalize_text)

    # Standardize merchant column
    df["merchant"] = (
        df["merchant"]
        .str.lower()
        .str.replace(r"[^a-z\s]", "", regex=True)
        .str.strip()
    )

    # Derive time features
    df = derive_time_features(df)

    # Reorder columns for clarity
    ordered_cols = [
        "transaction_id",
        "transaction_date",
        "timestamp",
        "amount",
        "currency",
        "payment_method",
        "is_credit",
        "merchant",
        "clean_description",
        "category",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_night",
        "is_amount_anomaly",
        "is_frequency_anomaly",
        "is_merchant_anomaly",
    ]

    return df[ordered_cols]

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    cleaned_df = clean_dataset(INPUT_FILE)
    cleaned_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Cleaned dataset written to {OUTPUT_FILE}")
