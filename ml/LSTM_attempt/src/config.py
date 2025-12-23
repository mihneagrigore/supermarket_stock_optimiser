from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    # Data paths
    DATA_PATH: Path = Path("../data/Grocery_Inventory new v1.csv")
    
    # Output paths
    MODEL_DIR: Path = Path("models/demand_lstm")
    BEST_PATH: Path = MODEL_DIR / "best.keras"
    MODEL_PATH: Path = MODEL_DIR / "model.keras"
    
    # Sequence parameters (adjusted for sparse snapshot data)
    LOOKBACK: int = 3    # Use last 3 snapshots
    HORIZON: int = 1     # Predict next snapshot
    
    # Training parameters
    BATCH_SIZE: int = 16
    EPOCHS: int = 200
    LEARNING_RATE: float = 0.001
    TEST_SIZE: float = 0.3
    RANDOM_STATE: int = 42
    
    # GOOD FEATURES ONLY (7 non-circular features)
    FEATURE_COLUMNS: tuple[str, ...] = (
        'Sales_Volume',              # Direct demand signal
        'Stock_Quantity',            # Current inventory level
        'Inventory_Turnover_Rate',   # Movement speed
        'stock_to_sales_ratio',      # Coverage metric (engineered)
        'days_until_expiration',     # Perishability (engineered)
        'Unit_Price',                # Economics
        'category_encoded',          # Product type (engineered)
    )
    
    # Target column
    TARGET_COLUMN: str = 'Reorder_Quantity'
    
    # EXCLUDED (circular features - DO NOT USE AS INPUTS)
    CIRCULAR_FEATURES: tuple[str, ...] = (
        'Reorder_Level',      # Circular: derived from reorder logic
        'Reorder_Quantity',   # This is our TARGET, not a feature
        'coverage_ratio',     # Uses Reorder_Level (circular)
        'needs_reorder',      # Uses Reorder_Level (circular)
        'stock_deficit',      # Uses Reorder_Level (circular)
    )
