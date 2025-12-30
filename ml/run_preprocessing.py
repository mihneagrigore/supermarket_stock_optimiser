import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from data.downloader import KaggleDownloader
from src.pipeline import PreprocessingPipeline
from config import RAW_DATA_PATH

# CONFIG
TEST_RATIO = 0.2
DATE_COL = "date"
TARGET_COL = "units_sold"
PRODUCT_COL = "product_id"
PREPROCESSED_DIR = Path("data/preprocessed")
LOOKBACK = 28  # Use same as LSTM config
HORIZON = 7    # Forecast horizon
USE_LOG_TARGET = True  # Apply log1p to target for stability


def create_sequences_per_product(df, X_encoded, y_values, product_ids, lookback, horizon, use_log_target=False):
    """
    Create LSTM sequences without crossing product boundaries.
    
    For each product:
    - Extract that product's contiguous rows
    - Create sliding windows only within that product's data
    - Target y[t] = sum(units_sold[t:t+horizon]) for that product
    - If use_log_target, apply log1p to the summed target
    """
    X_seq, y_seq = [], []
    
    unique_products = product_ids.unique()
    
    for product in unique_products:
        # Get indices for this product
        mask = product_ids == product
        idx = np.where(mask)[0]
        
        if len(idx) < lookback + horizon:
            # Not enough data for this product
            continue
        
        X_product = X_encoded[idx]
        y_product = y_values[idx]  # Raw units_sold values (not transformed yet)
        
        # Create sequences within this product only
        for i in range(len(X_product) - lookback - horizon + 1):
            X_seq.append(X_product[i:i+lookback])
            # Target is sum of next 'horizon' days for this product
            horizon_sum = y_product[i+lookback:i+lookback+horizon].sum()
            # Apply log1p AFTER summing if requested
            if use_log_target:
                horizon_sum = np.log1p(horizon_sum)
            y_seq.append(horizon_sum)
    
    return np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.float32)


def split_by_time_per_product(df, test_ratio=0.2):
    """
    Split data by time within each product.
    Last test_ratio of each product's dates go to test set.
    """
    train_dfs = []
    test_dfs = []
    
    for product_id, group in df.groupby(PRODUCT_COL):
        group = group.sort_values(DATE_COL).reset_index(drop=True)
        split_idx = int(len(group) * (1 - test_ratio))
        train_dfs.append(group.iloc[:split_idx])
        test_dfs.append(group.iloc[split_idx:])
    
    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)
    
    return train_df, test_df


# Download
downloader = KaggleDownloader()
downloader.download()

# Load raw data
df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")

# Preprocess (now aggregates by product_id, date)
pipeline = PreprocessingPipeline()
processed_df = pipeline.run(df)

# Sort by product_id then date for proper sequence creation
processed_df = processed_df.sort_values([PRODUCT_COL, DATE_COL]).reset_index(drop=True)

# Split by time within each product
train_df, test_df = split_by_time_per_product(processed_df, TEST_RATIO)

print("\n================ SPLIT SUMMARY ================\n")
print(f"Total rows       : {len(processed_df)}")
print(f"Train rows       : {len(train_df)}")
print(f"Test rows        : {len(test_df)}")
print(f"Unique products  : {processed_df[PRODUCT_COL].nunique()}")

print("\nTraining period (per product):")
print(f"  Dates: {train_df[DATE_COL].min()} → {train_df[DATE_COL].max()}")

print("\nTesting period (per product):")
print(f"  Dates: {test_df[DATE_COL].min()} → {test_df[DATE_COL].max()}")

# Prepare features (exclude date, target, and product_id from features)
feature_cols = [c for c in train_df.columns if c not in [DATE_COL, TARGET_COL, PRODUCT_COL]]
print(f"\nFeature columns: {feature_cols}")

X_train = train_df[feature_cols].copy()
y_train = train_df[TARGET_COL].copy()
train_products = train_df[PRODUCT_COL].copy()

X_test = test_df[feature_cols].copy()
y_test = test_df[TARGET_COL].copy()
test_products = test_df[PRODUCT_COL].copy()

# One-hot encode 'seasonality' if present
if 'seasonality' in X_train.columns:
    X_train = pd.get_dummies(X_train, columns=['seasonality'], prefix='season')
    X_test = pd.get_dummies(X_test, columns=['seasonality'], prefix='season')
    # Align columns between train and test (fill missing with 0)
    X_train, X_test = X_train.align(X_test, join='left', axis=1, fill_value=0)

# Store final feature column order for inference
feature_columns = list(X_train.columns)
print(f"\nEncoded feature columns ({len(feature_columns)}):")
print(feature_columns)

# Create LSTM sequences per product (no cross-product contamination)
# Log transformation is applied INSIDE create_sequences_per_product AFTER summing horizon
print(f"\nCreating LSTM sequences per product (lookback={LOOKBACK}, horizon={HORIZON})...")
print(f"Log transform target: {USE_LOG_TARGET}")

X_train_seq, y_train_seq = create_sequences_per_product(
    train_df,
    X_train.values.astype(np.float32),
    y_train.values.astype(np.float32),  # Pass RAW y values, log applied after sum
    train_products,
    LOOKBACK,
    HORIZON,
    use_log_target=USE_LOG_TARGET
)

X_test_seq, y_test_seq = create_sequences_per_product(
    test_df,
    X_test.values.astype(np.float32),
    y_test.values.astype(np.float32),  # Pass RAW y values, log applied after sum
    test_products,
    LOOKBACK,
    HORIZON,
    use_log_target=USE_LOG_TARGET
)

print(f"\nSequence shapes:")
print(f"  X_train: {X_train_seq.shape}, y_train: {y_train_seq.shape}")
print(f"  X_test:  {X_test_seq.shape}, y_test:  {y_test_seq.shape}")

# Print target statistics to verify per-product scale
if USE_LOG_TARGET:
    print(f"\nTarget statistics (log-transformed):")
    print(f"  y_train: mean={y_train_seq.mean():.2f}, std={y_train_seq.std():.2f}, min={y_train_seq.min():.2f}, max={y_train_seq.max():.2f}")
    print(f"  y_test:  mean={y_test_seq.mean():.2f}, std={y_test_seq.std():.2f}, min={y_test_seq.min():.2f}, max={y_test_seq.max():.2f}")
    print(f"\nOriginal scale (expm1):")
    print(f"  y_train: mean={np.expm1(y_train_seq).mean():.2f}, max={np.expm1(y_train_seq).max():.2f}")
else:
    print(f"\nTarget statistics:")
    print(f"  y_train: mean={y_train_seq.mean():.2f}, std={y_train_seq.std():.2f}, min={y_train_seq.min():.2f}, max={y_train_seq.max():.2f}")
    print(f"  y_test:  mean={y_test_seq.mean():.2f}, std={y_test_seq.std():.2f}")

# Save preprocessed data
PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

np.save(PREPROCESSED_DIR / "X_train.npy", X_train_seq)
np.save(PREPROCESSED_DIR / "y_train.npy", y_train_seq)
np.save(PREPROCESSED_DIR / "X_test.npy", X_test_seq)
np.save(PREPROCESSED_DIR / "y_test.npy", y_test_seq)

# Save preprocessing artifacts for inference consistency
artifacts = {
    "feature_columns": feature_columns,
    "lookback": LOOKBACK,
    "horizon": HORIZON,
    "use_log_target": USE_LOG_TARGET,
    "products": list(processed_df[PRODUCT_COL].unique()),
}
joblib.dump(artifacts, PREPROCESSED_DIR / "preprocess_artifacts.pkl")

print(f"\nSaved preprocessed data to {PREPROCESSED_DIR}/")
print(f"Saved preprocessing artifacts (feature_columns, config) to preprocess_artifacts.pkl")


def load_preprocessed_data():
    """Load preprocessed train/test data."""
    X_train = np.load(PREPROCESSED_DIR / "X_train.npy")
    y_train = np.load(PREPROCESSED_DIR / "y_train.npy")
    X_test = np.load(PREPROCESSED_DIR / "X_test.npy")
    y_test = np.load(PREPROCESSED_DIR / "y_test.npy")
    return X_train, y_train, X_test, y_test


def load_preprocessing_artifacts():
    """Load preprocessing artifacts for inference."""
    return joblib.load(PREPROCESSED_DIR / "preprocess_artifacts.pkl")
