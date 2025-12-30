from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import tensorflow as tf
import joblib

from src.config import Config
from config import RAW_DATA_PATH, PRODUCT_ID

# Path to preprocessing artifacts
PREPROCESSED_DIR = Path(__file__).parent.parent / "data" / "preprocessed"


def load_preprocessing_artifacts():
    """Load preprocessing artifacts saved during training."""
    artifacts_path = PREPROCESSED_DIR / "preprocess_artifacts.pkl"
    if not artifacts_path.exists():
        return None
    return joblib.load(artifacts_path)


def load_all_products():
    """Load raw data and return available product IDs."""
    from src.cleaner import DataCleaner
    
    df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")
    cleaner = DataCleaner()
    df = cleaner.clean(df)
    products = sorted(df["product_id"].unique())
    return df, products


def load_product_data(product_id: str):
    """Load and preprocess data for a specific product."""
    from src.cleaner import DataCleaner
    from src.feature_engineer import FeatureEngineer
    
    # Load raw data
    df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")
    
    # Clean data
    cleaner = DataCleaner()
    df = cleaner.clean(df)
    
    # Filter for specific product
    df = df[df["product_id"] == product_id].copy()
    
    if len(df) == 0:
        raise ValueError(f"No data found for product_id: {product_id}")
    
    # Aggregate by date for this single product (sum across stores)
    df = (
        df.groupby("date", as_index=False)
          .agg({
              "units_sold": "sum",
              "inventory_level": "sum",
              "units_ordered": "sum",
              "price": "mean",
              "discount": "mean",
              "holiday_promotion": "max",
              "seasonality": "first"
          })
    )
    
    # Keep product_id for lag feature computation (even though it's a single value)
    df["product_id"] = product_id
    
    df = df[
        [
            "product_id",
            "date",
            "units_sold",
            "inventory_level",
            "units_ordered",
            "price",
            "discount",
            "holiday_promotion",
            "seasonality"
        ]
    ]
    
    # Add features (lag features now use groupby, but since single product, it works the same)
    fe = FeatureEngineer()
    df = fe.add_calendar_features(df)
    df = fe.add_lag_features(df, group_col="product_id")
    
    df = df.dropna().reset_index(drop=True)
    
    return df


def create_lookback_window(df: pd.DataFrame, lookback: int = 28, artifacts: dict = None):
    """
    Create a lookback window from the most recent data.
    Uses saved artifacts to ensure feature column consistency with training.
    """
    # Sort by date and take last lookback rows
    df = df.sort_values('date').reset_index(drop=True)
    
    if len(df) < lookback:
        raise ValueError(f"Need at least {lookback} rows, got {len(df)}")
    
    # Drop date, target, and product_id from features
    feature_cols = [c for c in df.columns if c not in ['date', 'units_sold', 'product_id']]
    
    # One-hot encode seasonality if present
    df_encoded = df[feature_cols].copy()
    if 'seasonality' in df_encoded.columns:
        df_encoded = pd.get_dummies(df_encoded, columns=['seasonality'], prefix='season')
    
    # Reindex to match training feature columns exactly
    if artifacts is not None and "feature_columns" in artifacts:
        training_columns = artifacts["feature_columns"]
        # Reindex to match training columns, fill missing with 0
        df_encoded = df_encoded.reindex(columns=training_columns, fill_value=0)
    
    # Get last lookback rows
    window = df_encoded.iloc[-lookback:].values.astype(np.float32)
    
    # Reshape for LSTM: (1, lookback, features)
    return window[None, :, :]


def predict_next_horizon(model, df: pd.DataFrame, cfg: Config, artifacts: dict = None):
    """Predict demand for next horizon days."""
    window = create_lookback_window(df, cfg.LOOKBACK, artifacts)
    
    # Predict (raw model output)
    raw_forecast = float(model.predict(window, verbose=0).reshape(-1)[0])
    
    # If training used log1p, apply expm1 to reverse the transformation
    if artifacts is not None and artifacts.get("use_log_target", False):
        forecast = np.expm1(raw_forecast)
    else:
        forecast = raw_forecast
    
    # Calculate metrics from historical data and forecast
    recent_sales = df['units_sold'].tail(cfg.LOOKBACK).values
    historical_daily_mean = recent_sales.mean()
    historical_daily_std = recent_sales.std()
    
    # Use forecast-based daily mean for reorder calculations
    forecast_daily_mean = forecast / cfg.HORIZON
    
    # Compute reorder point using forecast (not historical)
    # ROP = (Lead Time Demand) + Safety Stock
    lead_time = cfg.DEFAULT_LEAD_TIME_DAYS
    lead_time_demand = forecast_daily_mean * lead_time
    
    # Safety stock based on historical variability during lead time
    # sigma_LT = daily_std * sqrt(lead_time)
    sigma_lt = historical_daily_std * np.sqrt(lead_time)
    safety_stock = cfg.SERVICE_LEVEL_Z * sigma_lt
    rop = lead_time_demand + safety_stock
    
    # Order-up-to level (covers lead time + review period)
    review_period_days = cfg.HORIZON  # Use forecast horizon as review period
    order_up_to = rop + forecast_daily_mean * review_period_days
    
    # Get current inventory if available
    current_inventory = df['inventory_level'].iloc[-1] if 'inventory_level' in df.columns else 0
    
    # Recommended reorder quantity
    reorder_qty = max(0, order_up_to - current_inventory)
    
    return {
        "forecast_horizon_demand": forecast,
        "forecast_daily_mean": forecast_daily_mean,
        "historical_daily_mean": historical_daily_mean,
        "historical_daily_std": historical_daily_std,
        "lead_time_days": lead_time,
        "safety_stock": safety_stock,
        "reorder_point_units": rop,
        "current_inventory": current_inventory,
        "order_up_to_level": order_up_to,
        "recommended_reorder_qty": reorder_qty,
    }


def main():
    cfg = Config()
    
    # Load preprocessing artifacts for feature consistency
    artifacts = load_preprocessing_artifacts()
    if artifacts:
        print(f"Loaded preprocessing artifacts:")
        print(f"  - Feature columns: {len(artifacts.get('feature_columns', []))} features")
        print(f"  - Log target: {artifacts.get('use_log_target', False)}")
    else:
        print("Warning: No preprocessing artifacts found. Feature alignment may be inconsistent.")
    
    # Load model
    print(f"\nLoading model from {cfg.MODEL_PATH}...")
    model = tf.keras.models.load_model(cfg.MODEL_PATH)
    
    # Load data for the product
    print(f"Loading data for product: {PRODUCT_ID}...")
    df = load_product_data(PRODUCT_ID)
    
    print(f"Data loaded: {len(df)} days of data")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Make prediction
    print(f"\nPredicting demand for next {cfg.HORIZON} days...")
    result = predict_next_horizon(model, df, cfg, artifacts)
    
    print("\n" + "="*60)
    print(f"PREDICTION RESULTS FOR {PRODUCT_ID}")
    print("="*60)
    for k, v in result.items():
        if isinstance(v, float):
            print(f"{k:30s}: {v:>10.2f}")
        else:
            print(f"{k:30s}: {v}")
    print("="*60)


if __name__ == "__main__":
    main()
