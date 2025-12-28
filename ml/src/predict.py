from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import tensorflow as tf

from src.config import Config
from config import RAW_DATA_PATH, PRODUCT_ID

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
    from src.pipeline import PreprocessingPipeline
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
    
    # Aggregate by date
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
    
    df = df[
        [
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
    
    # Add features
    fe = FeatureEngineer()
    df = fe.add_calendar_features(df)
    df = fe.add_lag_features(df)
    
    df = df.dropna().reset_index(drop=True)
    
    return df

def create_lookback_window(df: pd.DataFrame, lookback: int = 28):
    """Create a lookback window from the most recent data."""
    # Sort by date and take last lookback rows
    df = df.sort_values('date').reset_index(drop=True)
    
    if len(df) < lookback:
        raise ValueError(f"Need at least {lookback} rows, got {len(df)}")
    
    # Drop date and target
    feature_cols = [c for c in df.columns if c not in ['date', 'units_sold']]
    
    # One-hot encode seasonality if present
    df_encoded = df[feature_cols].copy()
    if 'seasonality' in df_encoded.columns:
        df_encoded = pd.get_dummies(df_encoded, columns=['seasonality'], prefix='season')
    
    # Get last lookback rows
    window = df_encoded.iloc[-lookback:].values.astype(np.float32)
    
    # Reshape for LSTM: (1, lookback, features)
    return window[None, :, :]

def predict_next_horizon(model, df: pd.DataFrame, cfg: Config):
    """Predict demand for next horizon days."""
    window = create_lookback_window(df, cfg.LOOKBACK)
    
    # Predict
    forecast = float(model.predict(window, verbose=0).reshape(-1)[0])
    
    # Calculate metrics from historical data
    recent_sales = df['units_sold'].tail(cfg.LOOKBACK).values
    daily_mean = recent_sales.mean()
    daily_std = recent_sales.std()
    
    # Compute reorder point
    lead_time = cfg.DEFAULT_LEAD_TIME_DAYS
    mu_lt = daily_mean * lead_time
    sigma_lt = daily_std * np.sqrt(lead_time)
    rop = mu_lt + cfg.SERVICE_LEVEL_Z * sigma_lt
    
    # Compute reorder quantity (order-up-to policy)
    review_buffer_days = 7.0
    order_up_to = rop + daily_mean * review_buffer_days
    
    # Get current inventory if available
    current_inventory = df['inventory_level'].iloc[-1] if 'inventory_level' in df.columns else 0
    reorder_qty = max(0, order_up_to - current_inventory)
    
    return {
        "forecast_horizon_demand": forecast,
        "forecast_daily_mean": forecast / cfg.HORIZON,
        "historical_daily_mean": daily_mean,
        "historical_daily_std": daily_std,
        "lead_time_days": lead_time,
        "reorder_point_units": rop,
        "current_inventory": current_inventory,
        "order_up_to_level": order_up_to,
        "recommended_reorder_qty": reorder_qty,
    }

def main():
    cfg = Config()
    
    # Load model trained on PRODUCT_ID
    print(f"Loading model from {cfg.MODEL_PATH}...")
    model = tf.keras.models.load_model(cfg.MODEL_PATH)
    
    # Load data for the same product used in training
    print(f"Loading data for product: {PRODUCT_ID} (same as training)...")
    df = load_product_data(PRODUCT_ID)
    
    print(f"Data loaded: {len(df)} days of data")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Make prediction
    print(f"\nPredicting demand for next {cfg.HORIZON} days...")
    result = predict_next_horizon(model, df, cfg)
    
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
