import pandas as pd
import numpy as np
from pathlib import Path
from data.downloader import KaggleDownloader
from src.pipeline import PreprocessingPipeline
from config import RAW_DATA_PATH

# CONFIG
TEST_RATIO = 0.2
DATE_COL = "date"
TARGET_COL = "units_sold"
PREPROCESSED_DIR = Path("data/preprocessed")
LOOKBACK = 28  # Use same as LSTM config
HORIZON = 7    # Forecast horizon


# Download
downloader = KaggleDownloader()
downloader.download()

# Load raw data
df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")

# Preprocess
pipeline = PreprocessingPipeline()
processed_df = pipeline.run(df)

processed_df = processed_df.sort_values(DATE_COL).reset_index(drop=True)

split_idx = int(len(processed_df) * (1 - TEST_RATIO))

# Split
train_df = processed_df.iloc[:split_idx].copy()
test_df = processed_df.iloc[split_idx:].copy()

X_train = train_df.drop(columns=[DATE_COL, TARGET_COL])
y_train = train_df[TARGET_COL]

X_test = test_df.drop(columns=[DATE_COL, TARGET_COL])
y_test = test_df[TARGET_COL]


print("\n================ SPLIT SUMMARY ================\n")
print(f"Total rows    : {len(processed_df)}")
print(f"Train rows    : {len(train_df)}")
print(f"Test rows     : {len(test_df)}")

print("\nTraining period:")
print(train_df[DATE_COL].min(), "→", train_df[DATE_COL].max())

print("\nTesting period:")
print(test_df[DATE_COL].min(), "→", test_df[DATE_COL].max())

print("\nFeature columns:")
print(list(X_train.columns))

# Encode categorical columns before saving
X_train_encoded = X_train.copy()
X_test_encoded = X_test.copy()

# One-hot encode 'seasonality' if present
if 'seasonality' in X_train_encoded.columns:
    X_train_encoded = pd.get_dummies(X_train_encoded, columns=['seasonality'], prefix='season')
    X_test_encoded = pd.get_dummies(X_test_encoded, columns=['seasonality'], prefix='season')
    # Align columns between train and test
    X_train_encoded, X_test_encoded = X_train_encoded.align(X_test_encoded, join='left', axis=1, fill_value=0)

print("\nEncoded feature columns:")
print(list(X_train_encoded.columns))

# Create LSTM sequences (lookback, horizon)
def create_sequences(X, y, lookback, horizon):
    """Create sliding window sequences for LSTM."""
    X_seq, y_seq = [], []
    for i in range(len(X) - lookback - horizon + 1):
        X_seq.append(X[i:i+lookback])
        # Target is sum of next 'horizon' days
        y_seq.append(y[i+lookback:i+lookback+horizon].sum())
    return np.array(X_seq), np.array(y_seq)

print(f"\nCreating LSTM sequences (lookback={LOOKBACK}, horizon={HORIZON})...")
X_train_seq, y_train_seq = create_sequences(
    X_train_encoded.values.astype(np.float32),
    y_train.values.astype(np.float32),
    LOOKBACK,
    HORIZON
)
X_test_seq, y_test_seq = create_sequences(
    X_test_encoded.values.astype(np.float32),
    y_test.values.astype(np.float32),
    LOOKBACK,
    HORIZON
)

print(f"Sequence shapes: X_train={X_train_seq.shape}, y_train={y_train_seq.shape}")
print(f"                 X_test={X_test_seq.shape}, y_test={y_test_seq.shape}")

# Save preprocessed data
PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

np.save(PREPROCESSED_DIR / "X_train.npy", X_train_seq)
np.save(PREPROCESSED_DIR / "y_train.npy", y_train_seq)
np.save(PREPROCESSED_DIR / "X_test.npy", X_test_seq)
np.save(PREPROCESSED_DIR / "y_test.npy", y_test_seq)

print(f"\nSaved preprocessed data to {PREPROCESSED_DIR}/")


def load_preprocessed_data():
    """Load preprocessed train/test data."""
    X_train = np.load(PREPROCESSED_DIR / "X_train.npy")
    y_train = np.load(PREPROCESSED_DIR / "y_train.npy")
    X_test = np.load(PREPROCESSED_DIR / "X_test.npy")
    y_test = np.load(PREPROCESSED_DIR / "y_test.npy")
    return X_train, y_train, X_test, y_test
