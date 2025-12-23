"""
LSTM data preparation using real snapshots (no forward-filling).
Uses ONLY non-circular features for training.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def load_data(data_path: Path = Path("../data/Grocery_Inventory new v1.csv")) -> pd.DataFrame:
    """Load raw CSV."""
    return pd.read_csv(data_path)


def clean_data(df: pd.DataFrame, lookback: int, horizon: int) -> tuple:
    """
    Clean data and create sequences from real snapshots (no forward-filling).
    Uses ONLY good non-circular features.
    
    Returns:
        (X_train, y_train, X_test, y_test) as 3D arrays for LSTM
    """
    df = df.copy()
    
    print("="*70)
    print("LSTM DATA PREPARATION - SNAPSHOT-BASED")
    print("="*70)
    print(f"\nRaw data: {len(df)} rows")
    
    # Parse dates
    df['Date_Received'] = pd.to_datetime(df['Date_Received'], format='mixed', errors='coerce')
    df['Expiration_Date'] = pd.to_datetime(df['Expiration_Date'], format='mixed', errors='coerce')
    
    # Parse Unit_Price
    if 'Unit_Price' in df.columns:
        df['Unit_Price'] = df['Unit_Price'].astype(str).str.replace('$', '').str.replace(',', '')
        df['Unit_Price'] = pd.to_numeric(df['Unit_Price'], errors='coerce')
    
    # Parse numeric columns
    df['Inventory_Turnover_Rate'] = pd.to_numeric(df['Inventory_Turnover_Rate'], errors='coerce')
    for col in ['Stock_Quantity', 'Reorder_Quantity', 'Sales_Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with missing critical fields
    required_cols = ['Date_Received', 'Expiration_Date', 'Reorder_Quantity', 
                     'Product_Name', 'Stock_Quantity', 'Sales_Volume', 'Unit_Price']
    df = df.dropna(subset=required_cols)
    print(f"After cleaning: {len(df)} rows")
    
    # Engineer GOOD features only (no circular dependencies)
    print("\nEngineering features (non-circular only)...")
    df['days_until_expiration'] = (df['Expiration_Date'] - df['Date_Received']).dt.days
    df['days_until_expiration'] = df['days_until_expiration'].fillna(365).clip(lower=0, upper=730)
    
    df['stock_to_sales_ratio'] = df['Stock_Quantity'] / (df['Sales_Volume'] + 1)
    
    if 'Catagory' in df.columns:
        df['category_encoded'] = pd.Categorical(df['Catagory']).codes
    else:
        df['category_encoded'] = 0
    
    # Fill remaining NaNs in features
    df['Inventory_Turnover_Rate'] = df['Inventory_Turnover_Rate'].fillna(
        df['Inventory_Turnover_Rate'].median()
    )
    
    # Sort by product and date
    df = df.sort_values(['Product_Name', 'Date_Received'])
    
    # Define GOOD features (7 non-circular features)
    GOOD_FEATURES = [
        'Sales_Volume',
        'Stock_Quantity',
        'Inventory_Turnover_Rate',
        'stock_to_sales_ratio',
        'days_until_expiration',
        'Unit_Price',
        'category_encoded',
    ]
    
    # VERIFY: No circular features are used
    FORBIDDEN = ['Reorder_Level', 'coverage_ratio', 'needs_reorder', 'stock_deficit']
    for forbidden in FORBIDDEN:
        if forbidden in GOOD_FEATURES:
            raise ValueError(f"ERROR: Circular feature '{forbidden}' detected in feature list!")
    
    print(f"✓ Using {len(GOOD_FEATURES)} good features (no circular dependencies)")
    print(f"  Features: {GOOD_FEATURES}")
    
    # Create sequences per product (use actual snapshots)
    X_list, y_list = [], []
    products_used = 0
    products_skipped = 0
    
    for product, group in df.groupby('Product_Name'):
        group = group.dropna(subset=GOOD_FEATURES + ['Reorder_Quantity'])
        
        if len(group) < lookback + horizon:
            products_skipped += 1
            continue  # Skip products with insufficient snapshots
        
        products_used += 1
        features = group[GOOD_FEATURES].values
        targets = group['Reorder_Quantity'].values
        
        # Create sliding windows from actual snapshots
        for i in range(len(features) - lookback):
            X_seq = features[i:i+lookback]      # (lookback, n_features)
            y_val = targets[i+lookback]         # Predict reorder at lookback position
            X_list.append(X_seq)
            y_list.append(y_val)
    
    if len(X_list) == 0:
        raise ValueError(
            f"No sequences created. Products need >={lookback+1} snapshots.\n"
            f"Current: {products_used} products used, {products_skipped} skipped.\n"
            f"Try reducing LOOKBACK in config.py"
        )
    
    X = np.array(X_list, dtype=np.float32)  # (n_samples, lookback, n_features)
    y = np.array(y_list, dtype=np.float32)  # (n_samples,)
    
    print(f"\nSequence creation:")
    print(f"  Products with >={lookback+1} snapshots: {products_used}")
    print(f"  Products skipped (too few snapshots): {products_skipped}")
    print(f"  Total sequences created: {len(X)}")
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, shuffle=True
    )
    
    # Scale features (fit on train only to prevent data leakage)
    print("\nScaling features (StandardScaler on train set only)...")
    scaler = StandardScaler()
    n_samples, lookback_len, n_features = X_train.shape
    
    # Flatten, scale, reshape
    X_train_flat = X_train.reshape(-1, n_features)
    X_train_scaled = scaler.fit_transform(X_train_flat).reshape(n_samples, lookback_len, n_features)
    
    X_test_flat = X_test.reshape(-1, n_features)
    X_test_scaled = scaler.transform(X_test_flat).reshape(X_test.shape[0], lookback_len, n_features)
    
    print(f"\nFinal dataset:")
    print(f"  Train samples: {len(X_train)} sequences")
    print(f"  Test samples: {len(X_test)} sequences")
    print(f"  Input shape: (lookback={lookback_len}, features={n_features})")
    print(f"  Target range: [{y.min():.1f}, {y.max():.1f}]")
    print(f"  Target mean: {y.mean():.1f}")
    print("="*70)
    
    return X_train_scaled, y_train, X_test_scaled, y_test
