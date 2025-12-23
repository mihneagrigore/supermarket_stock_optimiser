from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from typing import Tuple
import warnings
warnings.filterwarnings('ignore')


class InventoryDataPreprocessor:
    
    def __init__(self, lookback_days: int = 28, horizon_days: int = 7):
        self.lookback = lookback_days
        self.horizon = horizon_days
        self.scaler = None
        self.feature_columns = None
        
    def load_data(self, filepath: str = "data/Grocery_Inventory new v1.csv") -> pd.DataFrame:
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} rows with {df.shape[1]} columns")
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        allowed_cols = [
            'Product_Name', 'Date_Received', 'Last_Order_Date', 
            'Expiration_Date', 'Stock_Quantity', 'Reorder_Level', 
            'Reorder_Quantity', 'Sales_Volume', 'Inventory_Turnover_Rate'
        ]
        
        available_cols = [col for col in allowed_cols if col in df.columns]
        df = df[available_cols].copy()
        
        print(f"Retained {len(available_cols)} allowed columns")
        
        date_cols = ['Date_Received', 'Last_Order_Date', 'Expiration_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        initial_rows = len(df)
        df = df.dropna(subset=['Date_Received', 'Product_Name'])
        print(f"Removed {initial_rows - len(df)} rows with missing Date_Received or Product_Name")
        
        numeric_cols = ['Stock_Quantity', 'Reorder_Level', 'Reorder_Quantity', 
                       'Sales_Volume', 'Inventory_Turnover_Rate']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0).clip(lower=0)
        
        df = df.sort_values('Date_Received').drop_duplicates(
            subset=['Product_Name', 'Date_Received'], 
            keep='last'
        )
        
        print(f"Final dataset: {len(df)} rows after cleaning")
        return df
    
    def create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df = df.sort_values(['Product_Name', 'Date_Received']).reset_index(drop=True)
        
        df['day_of_week'] = df['Date_Received'].dt.dayofweek
        df['day_of_month'] = df['Date_Received'].dt.day
        df['month'] = df['Date_Received'].dt.month
        df['quarter'] = df['Date_Received'].dt.quarter
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        if 'Expiration_Date' in df.columns:
            df['days_to_expiry'] = (df['Expiration_Date'] - df['Date_Received']).dt.days
            df['days_to_expiry'] = df['days_to_expiry'].fillna(365).clip(lower=0, upper=730)
        
        if 'Last_Order_Date' in df.columns:
            df['days_since_last_order'] = (df['Date_Received'] - df['Last_Order_Date']).dt.days
            df['days_since_last_order'] = df['days_since_last_order'].fillna(0).clip(lower=0)
        
        print(f"Created temporal features")
        return df
    
    def aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:

        agg_dict = {
            'Stock_Quantity': 'last',
            'Reorder_Level': 'last',       
            'Reorder_Quantity': 'last',    
            'Sales_Volume': 'sum',         
            'Inventory_Turnover_Rate': 'mean',  
            'days_to_expiry': 'min',       
            'days_since_last_order': 'last',
            'day_of_week': 'first',
            'day_of_month': 'first',
            'month': 'first',
            'quarter': 'first',
            'is_weekend': 'first'
        }
        
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
        
        df_daily = df.groupby(['Product_Name', 'Date_Received'], as_index=False).agg(agg_dict)
        
        print(f"Aggregated to {len(df_daily)} daily product records")
        return df_daily
    
    def fill_missing_dates(self, df: pd.DataFrame, min_history_days: int = 60) -> pd.DataFrame:
        complete_series = []
        
        for product, group in df.groupby('Product_Name'):
            group = group.sort_values('Date_Received')
            
            date_range_days = (group['Date_Received'].max() - group['Date_Received'].min()).days
            if date_range_days < min_history_days:
                continue
            
            date_range = pd.date_range(
                start=group['Date_Received'].min(),
                end=group['Date_Received'].max(),
                freq='D'
            )
            
            group = group.set_index('Date_Received').reindex(date_range)
            
            ffill_cols = ['Stock_Quantity', 'Reorder_Level', 'Reorder_Quantity', 
                         'Inventory_Turnover_Rate', 'days_to_expiry', 'days_since_last_order']
            for col in ffill_cols:
                if col in group.columns:
                    group[col] = group[col].fillna(method='ffill').fillna(0)
            
            if 'Sales_Volume' in group.columns:
                group['Sales_Volume'] = group['Sales_Volume'].fillna(0)
            
            group['day_of_week'] = group.index.dayofweek
            group['day_of_month'] = group.index.day
            group['month'] = group.index.month
            group['quarter'] = group.index.quarter
            group['is_weekend'] = (group.index.dayofweek >= 5).astype(int)
            
            group['Product_Name'] = product
            group['Date_Received'] = group.index
            group = group.reset_index(drop=True)
            
            complete_series.append(group)
        
        if not complete_series:
            raise ValueError(f"No products have sufficient history (>= {min_history_days} days)")
        
        result = pd.concat(complete_series, ignore_index=True)
        print(f"Created complete time series for {result['Product_Name'].nunique()} products")
        print(f"Total daily records: {len(result)}")
        
        return result
    
    def create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values(['Product_Name', 'Date_Received'])
        
        windows = [7, 14, 30]
        
        for window in windows:
            if 'Sales_Volume' in df.columns:
                df[f'sales_ma_{window}d'] = df.groupby('Product_Name')['Sales_Volume'].transform(
                    lambda x: x.rolling(window=window, min_periods=1).mean()
                )
                
                df[f'sales_std_{window}d'] = df.groupby('Product_Name')['Sales_Volume'].transform(
                    lambda x: x.rolling(window=window, min_periods=1).std().fillna(0)
                )
        
        print(f"Created rolling features for windows: {windows}")
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:

        self.feature_columns = [
            'Stock_Quantity',
            'Reorder_Level',
            'Reorder_Quantity',
            'Sales_Volume',
            'Inventory_Turnover_Rate',
            'days_to_expiry',
            'days_since_last_order',
            'day_of_week',
            'day_of_month',
            'month',
            'quarter',
            'is_weekend',
            'sales_ma_7d',
            'sales_std_7d',
            'sales_ma_14d',
            'sales_std_14d',
            'sales_ma_30d',
            'sales_std_30d'
        ]
        
        self.feature_columns = [col for col in self.feature_columns if col in df.columns]
        
        print(f"Selected {len(self.feature_columns)} features: {self.feature_columns}")
        return df
    
    def create_sequences(self, df: pd.DataFrame, product_name: str) -> Tuple[np.ndarray, np.ndarray]:
    
        product_df = df[df['Product_Name'] == product_name].sort_values('Date_Received')
        
        features = product_df[self.feature_columns].values
        
        sales = product_df['Sales_Volume'].values
        
        X_sequences = []
        y_targets = []
        
        for i in range(len(features) - self.lookback - self.horizon + 1):
            X_sequences.append(features[i:i + self.lookback])
            
            y_targets.append(sales[i + self.lookback:i + self.lookback + self.horizon].sum())
        
        if len(X_sequences) == 0:
            return np.array([]), np.array([])
        
        return np.array(X_sequences), np.array(y_targets)
    
    def train_test_split(self, df: pd.DataFrame, test_fraction: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame]:
        train_parts = []
        test_parts = []
        
        for product, group in df.groupby('Product_Name'):
            group = group.sort_values('Date_Received')
            
            split_idx = int(len(group) * (1 - test_fraction))
            
            if split_idx < (self.lookback + self.horizon):
                continue
            
            if len(group) - split_idx < (self.lookback + self.horizon):
                continue
            
            train_parts.append(group.iloc[:split_idx])
            test_parts.append(group.iloc[split_idx:])
        
        if not train_parts:
            raise ValueError("No products have sufficient data for train/test split")
        
        df_train = pd.concat(train_parts, ignore_index=True)
        df_test = pd.concat(test_parts, ignore_index=True)
        
        print(f"\nTrain/Test Split:")
        print(f"  Training products: {df_train['Product_Name'].nunique()}")
        print(f"  Training records: {len(df_train)}")
        print(f"  Test products: {df_test['Product_Name'].nunique()}")
        print(f"  Test records: {len(df_test)}")
        
        return df_train, df_test
    
    def prepare_lstm_data(self, df: pd.DataFrame, fit_scaler: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        X_all = []
        y_all = []
        
        if fit_scaler:
            self.scaler = StandardScaler()
            all_features = df[self.feature_columns].values
            self.scaler.fit(all_features)
            print("Fitted StandardScaler on training data")
        
        products = df['Product_Name'].unique()
        skipped = 0
        
        for product in products:
            X_seq, y_seq = self.create_sequences(df, product)
            
            if len(X_seq) == 0:
                skipped += 1
                continue
            
            n_samples, lookback, n_features = X_seq.shape
            X_seq_reshaped = X_seq.reshape(-1, n_features)
            X_seq_scaled = self.scaler.transform(X_seq_reshaped)
            X_seq_scaled = X_seq_scaled.reshape(n_samples, lookback, n_features)
            
            X_all.append(X_seq_scaled)
            y_all.append(y_seq)
        
        if skipped > 0:
            print(f"Skipped {skipped} products due to insufficient sequence length")
        
        if not X_all:
            raise ValueError("No valid sequences created. Check lookback/horizon parameters.")
        
        X = np.concatenate(X_all, axis=0).astype('float32')
        y = np.concatenate(y_all, axis=0).astype('float32')
        
        print(f"Created {len(X)} sequences from {len(products) - skipped} products")
        print(f"X shape: {X.shape} (samples, lookback={self.lookback}, features={len(self.feature_columns)})")
        print(f"y shape: {y.shape}")
        
        return X, y


def load_data(filepath: str = "data/Grocery_Inventory new v1.csv") -> pd.DataFrame:
    preprocessor = InventoryDataPreprocessor()
    return preprocessor.load_data(filepath)


def clean_data(df: pd.DataFrame, lookback: int = 28, horizon: int = 7) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    print(f"\n{'='*60}")
    print(f"INVENTORY DATA PREPROCESSING PIPELINE")
    print(f"Lookback: {lookback} days | Horizon: {horizon} days")
    print(f"{'='*60}\n")
    
    preprocessor = InventoryDataPreprocessor(lookback_days=lookback, horizon_days=horizon)
    
    print("Step 1: Cleaning data...")
    df = preprocessor.clean_data(df)
    
    print("\nStep 2: Creating temporal features...")
    df = preprocessor.create_temporal_features(df)
    
    print("\nStep 3: Aggregating to daily level...")
    df = preprocessor.aggregate_to_daily(df)
    
    print("\nStep 4: Filling missing dates...")
    df = preprocessor.fill_missing_dates(df, min_history_days=lookback + horizon + 30)
    
    print("\nStep 5: Creating rolling features...")
    df = preprocessor.create_rolling_features(df)
    
    print("\nStep 6: Preparing features...")
    df = preprocessor.prepare_features(df)
    
    print("\nStep 7: Splitting train/test...")
    df_train, df_test = preprocessor.train_test_split(df, test_fraction=0.15)
    
    print("\nStep 8: Creating LSTM sequences...")
    print("\nProcessing training data...")
    X_train, y_train = preprocessor.prepare_lstm_data(df_train, fit_scaler=True)
    
    print("\nProcessing test data...")
    X_test, y_test = preprocessor.prepare_lstm_data(df_test, fit_scaler=False)
    
    print(f"\n{'='*60}")
    print(f"PREPROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"\nFinal Shapes:")
    print(f"  X_train: {X_train.shape}")
    print(f"  y_train: {y_train.shape}")
    print(f"  X_test: {X_test.shape}")
    print(f"  y_test: {y_test.shape}")
    print(f"\nData Statistics:")
    print(f"  Training samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")
    print(f"  Features per timestep: {X_train.shape[2]}")
    print(f"  Target range: [{y_train.min():.2f}, {y_train.max():.2f}]")
    print(f"{'='*60}\n")
    
    return X_train, y_train, X_test, y_test