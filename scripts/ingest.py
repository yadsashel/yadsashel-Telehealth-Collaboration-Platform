import os
import pandas as pd

# Define paths
RAW_PATH = "data/raw/heart_failure_clinical_records_dataset.csv"
CLEAN_DIR = "data/clean"
CLEAN_PATH = os.path.join(CLEAN_DIR, "heart_clean.csv")

def load_data(path):
    print("📥 Loading data...")
    return pd.read_csv(path)

def clean_data(df):
    print("🧹 Cleaning data...")
    # Drop rows with missing values
    df_clean = df.dropna()

    # Optionally validate numeric columns
    numeric_cols = df_clean.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    return df_clean

def save_data(df, path):
    print("💾 Saving cleaned data...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"✅ Cleaned data saved to: {path}")

def main():
    if not os.path.exists(RAW_PATH):
        print(f"❌ Raw file not found at: {RAW_PATH}")
        return

    df = load_data(RAW_PATH)
    df_clean = clean_data(df)
    save_data(df_clean, CLEAN_PATH)

if __name__ == "__main__":
    main()