#!/usr/bin/env python3
"""
Prediction script for feedforward neural network.
Predicts reorder quantity for a specific product using historical data.
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import tensorflow as tf

from src.config import Config
from data_prep import clean_data, engineer_features, load_scaler


def load_product_data(product_name: str, months_lookback: int, data_path: Path) -> pd.DataFrame:
    """Load and filter data for specific product."""
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Load data
    df = pd.read_csv(data_path)
    df['Date_Received'] = pd.to_datetime(df['Date_Received'], format='mixed', errors='coerce')
    
    # Filter by product name (case-insensitive)
    mask = df['Product_Name'].str.lower() == product_name.lower()
    product_df = df[mask].copy()
    
    if len(product_df) == 0:
        available = df['Product_Name'].unique()
        raise ValueError(
            f"Product '{product_name}' not found.\n"
            f"Available products (first 20): {', '.join(sorted(available)[:20])}..."
        )
    
    # Filter by time window
    max_date = product_df['Date_Received'].max()
    cutoff_date = max_date - timedelta(days=months_lookback * 30)
    product_df = product_df[product_df['Date_Received'] >= cutoff_date]
    
    if len(product_df) == 0:
        raise ValueError(f"No data found for '{product_name}' in last {months_lookback} months")
    
    product_df = product_df.sort_values('Date_Received')
    return product_df


def predict_for_product(cfg: Config, product_name: str, months_lookback: int):
    """Make prediction for a specific product."""
    
    print(f"\nLoading data for '{product_name}' (last {months_lookback} months)...")
    
    # Load product data
    df = load_product_data(product_name, months_lookback, cfg.DATA_PATH)
    
    # Clean and engineer features
    df = clean_data(df)
    df = engineer_features(df)
    
    # Load model and scaler
    print("Loading trained model and scaler...")
    model = tf.keras.models.load_model(cfg.BEST_PATH)
    scaler = load_scaler(cfg.SCALER_PATH)
    
    # Get latest snapshot
    latest = df.iloc[-1]
    
    # Prepare features
    X = df[list(cfg.FEATURE_COLUMNS)].iloc[[-1]].values.astype('float32')  # Last row
    X_scaled = scaler.transform(X)
    
    # Predict
    prediction = model.predict(X_scaled, verbose=0)[0, 0]
    
    # Calculate statistics
    avg_sales = df['Sales_Volume'].mean()
    avg_stock = df['Stock_Quantity'].mean()
    avg_turnover = df['Inventory_Turnover_Rate'].mean()
    
    return {
        'product_name': product_name,
        'current_stock': latest['Stock_Quantity'],
        'predicted_reorder_qty': prediction,
        'actual_reorder_qty': latest.get('Reorder_Quantity', None),
        'avg_sales': avg_sales,
        'avg_stock': avg_stock,
        'avg_turnover': avg_turnover,
        'unit_price': latest['Unit_Price'],
        'data_points': len(df),
        'date_range': f"{df['Date_Received'].min().date()} to {df['Date_Received'].max().date()}",
        'latest_date': df['Date_Received'].max().date()
    }


def print_results(results: dict):
    """Print prediction results."""
    print("\n" + "="*70)
    print("FEEDFORWARD NN REORDER PREDICTION")
    print("="*70)
    
    print(f"\nProduct: {results['product_name']}")
    print(f"Unit Price: ${results['unit_price']:.2f}")
    
    print(f"\n📊 Current Status:")
    print(f"  Current stock: {results['current_stock']:.0f} units")
    print(f"  Average sales: {results['avg_sales']:.1f} units/period")
    print(f"  Average turnover rate: {results['avg_turnover']:.1f}%")
    
    print(f"\n🎯 Neural Network Prediction:")
    print(f"  Predicted reorder quantity: {results['predicted_reorder_qty']:.1f} units")
    print(f"  Estimated reorder cost: ${results['predicted_reorder_qty'] * results['unit_price']:.2f}")
    
    if results['actual_reorder_qty'] is not None:
        error = abs(results['actual_reorder_qty'] - results['predicted_reorder_qty'])
        pct_error = (error / results['actual_reorder_qty'] * 100) if results['actual_reorder_qty'] > 0 else 0
        print(f"\n📈 Comparison with Actual:")
        print(f"  Actual reorder quantity: {results['actual_reorder_qty']:.0f} units")
        print(f"  Prediction error: {error:.1f} units ({pct_error:.1f}%)")
    
    print(f"\n📈 Historical Data:")
    print(f"  Data points analyzed: {results['data_points']}")
    print(f"  Date range: {results['date_range']}")
    print(f"  Latest snapshot: {results['latest_date']}")
    
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Predict optimal reorder quantity using Feedforward Neural Network'
    )
    
    parser.add_argument('product_name', type=str, help='Product name (use quotes if contains spaces)')
    parser.add_argument('months_lookback', type=int, help='Months of historical data to use')
    
    args = parser.parse_args()
    
    try:
        cfg = Config()
        results = predict_for_product(cfg, args.product_name, args.months_lookback)
        print_results(results)
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
