from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
	# Required columns in the clean DF
	COL_DATE: str = "date"          # datetime64[ns]
	COL_STORE: str = "store_id"
	COL_SKU: str = "sku_id"
	COL_DEMAND: str = "units_sold"  # numeric >= 0

	# Optional numeric features (will be used only if present)
	EXTRA_NUMERIC_FEATURES: tuple[str, ...] = (
		"price", "promo_flag", "on_hand", "day_of_week", "month"
	)

	# Inventory policy inputs
	COL_LEAD_TIME_DAYS: str = "lead_time_days"
	DEFAULT_LEAD_TIME_DAYS: int = 7

	# Safety stock z (≈ 95% service if demand ~ normal)
	SERVICE_LEVEL_Z: float = 1.645

	# EOQ inputs (optional; fallback defaults used if missing)
	COL_ORDER_COST: str = "order_cost"
	COL_HOLD_COST: str = "hold_cost"
	DEFAULT_ORDER_COST: float = 25.0
	DEFAULT_HOLD_COST: float = 1.0  # per unit per year

	# Modeling
	LOOKBACK: int = 28   # past days used
	HORIZON: int = 7     # predict total demand next 7 days
	BATCH_SIZE: int = 256
	EPOCHS: int = 50
	LEARNING_RATE: float = 1e-3
	VAL_SPLIT_TIME_FRACTION: float = 0.15

	# Output paths
	MODEL_DIR: Path = Path("models/demand_lstm")
	BEST_PATH: Path = MODEL_DIR / "best.keras"
	MODEL_PATH: Path = MODEL_DIR / "model.keras"
	PREPROCESS_PATH: Path = MODEL_DIR / "preprocess.pkl"
