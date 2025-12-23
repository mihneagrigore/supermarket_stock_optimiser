from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Configuration for feedforward neural network inventory optimization."""
    
    # Feature columns (7 non-circular features)
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
    
    # Model hyperparameters
    LEARNING_RATE: float = 0.001
    BATCH_SIZE: int = 32
    EPOCHS: int = 200
    DROPOUT_RATE_1: float = 0.3
    DROPOUT_RATE_2: float = 0.2
    
    # Training parameters
    TEST_SIZE: float = 0.3  # 30% test, 70% train
    RANDOM_STATE: int = 42
    VALIDATION_SPLIT: float = 0.0  # Will use test set for validation
    
    # Callbacks
    EARLY_STOPPING_PATIENCE: int = 50
    REDUCE_LR_PATIENCE: int = 20
    REDUCE_LR_FACTOR: float = 0.5
    MIN_LR: float = 1e-6
    
    # Output paths
    MODEL_DIR: Path = Path("models/feedforward_reorder")
    MODEL_PATH: Path = MODEL_DIR / "model.keras"
    BEST_PATH: Path = MODEL_DIR / "best.keras"
    SCALER_PATH: Path = MODEL_DIR / "scaler.pkl"
    HISTORY_PATH: Path = MODEL_DIR / "history.pkl"
    
    # Data path
    DATA_PATH: Path = Path("../data/Grocery_Inventory new v1.csv")
