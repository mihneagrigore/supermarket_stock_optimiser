"""
Configuration for formula-based inventory optimizer.
Uses Economic Order Quantity (EOQ) and Reorder Point (ROP) calculations.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OptimizerConfig:
    # Data paths
    DATA_PATH: Path = Path("../data/Grocery_Inventory new v1.csv")
    OUTPUT_DIR: Path = Path("../data/processed/optimizer_results")
    
    # Inventory management parameters
    HOLDING_COST_RATE: float = 0.25  # 25% annual holding cost
    ORDER_COST: float = 50.0  # Fixed cost per order ($)
    SERVICE_LEVEL: float = 0.95  # 95% service level
    SERVICE_LEVEL_Z: float = 1.65  # Z-score for 95% service level
    
    # Lead time (days to receive order)
    DEFAULT_LEAD_TIME_DAYS: int = 7
    
    # Safety stock multipliers by category (higher = more buffer)
    CATEGORY_SAFETY_MULTIPLIERS: dict = None
    
    # Perishability constraints (max order quantity as multiple of weekly demand)
    MAX_ORDER_WEEKS: dict = None
    
    def __post_init__(self):
        # Set default mutable values
        if self.CATEGORY_SAFETY_MULTIPLIERS is None:
            object.__setattr__(self, 'CATEGORY_SAFETY_MULTIPLIERS', {
                'Fruits & Vegetables': 1.5,  # Higher due to perishability
                'Dairy': 1.4,
                'Seafood': 1.6,
                'Bakery': 1.3,
                'Beverages': 1.0,
                'Oils & Fats': 0.8,
                'Grains & Pulses': 0.7,  # More stable
                'Snacks': 0.9,
            })
        
        if self.MAX_ORDER_WEEKS is None:
            object.__setattr__(self, 'MAX_ORDER_WEEKS', {
                'Fruits & Vegetables': 2,  # Max 2 weeks supply
                'Dairy': 3,
                'Seafood': 1,
                'Bakery': 2,
                'Beverages': 8,
                'Oils & Fats': 12,
                'Grains & Pulses': 12,
                'Snacks': 8,
            })
