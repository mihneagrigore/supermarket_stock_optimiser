"""
Snapshot-based data preprocessing for feedforward neural network.
Each inventory snapshot is treated as an independent sample (no sequences).
Excludes circular features (Reorder_Level, Reorder_Quantity).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import pickle


def load_data(data_path: Path) -> pd.DataFrame:
    """Load raw inventory snapshot CSV."""
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows from {data_path}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and parse raw inventory data.
    Handles dates, numeric columns, and Unit_Price parsing.
    """
    df = df.copy()
    
    # Parse dates
    date_cols = ['Date_Received', 'Last_Order_Date', 'Expiration_Date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
    
    # Clean numeric columns
    numeric_cols = ['Stock_Quantity', 'Sales_Volume', 'Inventory_Turnover_Rate', 'Reorder_Quantity']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Parse Unit_Price (remove $ symbol)
    if 'Unit_Price' in df.columns:
        df['Unit_Price'] = df['Unit_Price'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
        df['Unit_Price'] = pd.to_numeric(df['Unit_Price'], errors='coerce')
    
    # Drop rows with missing critical values (target and key features)
    required_cols = ['Stock_Quantity', 'Sales_Volume', 'Unit_Price', 'Reorder_Quantity', 
                     'Date_Received', 'Expiration_Date']
    df = df.dropna(subset=required_cols)
    
    print(f"After cleaning: {len(df)} rows")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features from raw data.
    Creates 3 new features: days_until_expiration, stock_to_sales_ratio, category_encoded.
    EXCLUDES circular features: Reorder_Level, Reorder_Quantity, coverage_ratio, needs_reorder.
    """
    df = df.copy()
    
    # Feature 1: days_until_expiration
    df['days_until_expiration'] = (df['Expiration_Date'] - df['Date_Received']).dt.days
    df['days_until_expiration'] = df['days_until_expiration'].fillna(365).clip(lower=0, upper=730)
    
    # Feature 2: stock_to_sales_ratio (avoid division by zero)
    df['stock_to_sales_ratio'] = df['Stock_Quantity'] / (df['Sales_Volume'] + 1)
    
    # Feature 3: category_encoded
    if 'Catagory' in df.columns:
        df['category_encoded'] = pd.Categorical(df['Catagory']).codes
    else:
        df['category_encoded'] = 0
    
    # Fill any remaining NaNs in original features
    df['Inventory_Turnover_Rate'] = df['Inventory_Turnover_Rate'].fillna(
        df['Inventory_Turnover_Rate'].median()
    )
    df['category_encoded'] = df['category_encoded'].fillna(0)
    
    print("Feature engineering complete")
    return df


def prepare_training_data(
    df: pd.DataFrame, 
    feature_cols: tuple[str, ...], 
    target_col: str,
    test_size: float = 0.2, 
    random_state: int = 42
):
    """
    Prepare features and target for training.
    Fits StandardScaler on training data only to prevent data leakage.
    
    Returns:
        X_train, X_test, y_train, y_test, scaler
    """
    # Drop rows with missing feature or target values
    df_clean = df.dropna(subset=list(feature_cols) + [target_col])
    
    print(f"\nAfter dropping NaNs: {len(df_clean)} rows")
    
    # Extract features and target
    X = df_clean[list(feature_cols)].values.astype('float32')
    y = df_clean[target_col].values.astype('float32')
    
    # Split data (random shuffle OK for snapshot data)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True
    )
    
    # Fit scaler on training data only
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    print(f"\nData split:")
    print(f"  Training samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Feature columns: {list(feature_cols)}")
    print(f"  Target range: [{y_train.min():.1f}, {y_train.max():.1f}]")
    print(f"  Target mean: {y_train.mean():.1f}")
    
    return X_train, X_test, y_train, y_test, scaler


def save_scaler(scaler: StandardScaler, path: Path):
    """Save StandardScaler for inference."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"Saved scaler to {path}")


def load_scaler(path: Path) -> StandardScaler:
    """Load StandardScaler."""
    with open(path, 'rb') as f:
        return pickle.load(f)


if __name__ == "__main__":
    # Test the pipeline
    from src.config import Config
    cfg = Config()
    
    print("Loading data...")
    df = load_data(cfg.DATA_PATH)
    
    print("\nCleaning data...")
    df_clean = clean_data(df)
    
    print("\nEngineering features...")
    df_engineered = engineer_features(df_clean)
    
    print("\nPreparing training data...")
    X_train, X_test, y_train, y_test, scaler = prepare_training_data(
        df_engineered, 
        cfg.FEATURE_COLUMNS, 
        cfg.TARGET_COLUMN,
        test_size=cfg.TEST_SIZE,
        random_state=cfg.RANDOM_STATE
    )
    
    print("\n✓ Data preparation successful!")
