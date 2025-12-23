import pandas as pd

class DataPreprocessor:
    def __init__(self):
        self.data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = None
    
    def load_data(self, file_path):
        self.data = pd.read_csv(file_path)
        return self.data
    
    def create_time_series_features(self):
        
        df = self.data.copy()
        
        # Sort by date
        if 'Date_Received' in df.columns:
            df = df.sort_values('Date_Received')
        
        # Create time-based features
        date_columns = ['Date_Received', 'Last_Order_Date', 'Expiration_Date']
        for col in date_columns:
            if col in df.columns:
                df[f'{col}_year'] = df[col].dt.year
                df[f'{col}_month'] = df[col].dt.month
                df[f'{col}_day'] = df[col].dt.day
                df[f'{col}_dayofweek'] = df[col].dt.dayofweek
                df[f'{col}_quarter'] = df[col].dt.quarter
                df[f'{col}_is_weekend'] = df[col].dt.dayofweek.isin([5, 6]).astype(int)
        
        # Days until expiration (important for stock planning)
        if 'Expiration_Date' in df.columns and 'Date_Received' in df.columns:
            df['days_until_expiration'] = (df['Expiration_Date'] - df['Date_Received']).dt.days
        
        # Days since last order
        if 'Last_Order_Date' in df.columns and 'Date_Received' in df.columns:
            df['days_since_last_order'] = (df['Date_Received'] - df['Last_Order_Date']).dt.days
        
        # Drop original date columns
        df = df.drop(columns=[col for col in date_columns if col in df.columns])
        
        # Handle Product_Name encoding
        if 'Product_Name' in df.columns:
            df = pd.get_dummies(df, columns=['Product_Name'], drop_first=True)
        
        # Drop rows with NaN created by lag features
        df = df.dropna()
        
        self.data = df
        return self.data
    
    def clean_data(self):
        df = self.data.copy()
        
        columns_to_drop = ['Category', 'Supplier_Name', 'Warehouse_Location', 
                          'Status', 'Product_ID', 'Supplier_ID', 'Unit_Price', 'percentage']
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
        
        date_columns = ['Date_Received', 'Last_Order_Date', 'Expiration_Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        df = df.dropna()

        self.data = self.create_time_series_features()
        return self.data