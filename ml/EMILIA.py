from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile
import pandas as pd
import numpy as np


@dataclass(frozen=True)
class EmiliaConfig:
	RAW_ZIP_PATH: Path = Path("data/raw/grocery_inventory.zip")

	# If None -> auto-pick first CSV in zip
	CSV_IN_ZIP: str | None = None

	# If True -> create DAILY rows per SKU/store so the LSTM has sequences to learn from
	EXPAND_TO_DAILY_SERIES: bool = True

	# If dates are missing/bad, expand over this many days ending at last_order_date (fallback)
	FALLBACK_WINDOW_DAYS: int = 60

	# If lead time not present in data, use this
	DEFAULT_LEAD_TIME_DAYS: int = 7


def _pick_csv_from_zip(zf: zipfile.ZipFile, preferred: str | None) -> str:
	if preferred:
		if preferred not in zf.namelist():
			raise FileNotFoundError(f"CSV_IN_ZIP='{preferred}' not found. First files: {zf.namelist()[:20]}")
		return preferred
	csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
	if not csvs:
		raise FileNotFoundError("No CSV found inside the zip.")
	return csvs[0]


def get_clean_dataframe(cfg: EmiliaConfig = EmiliaConfig()) -> pd.DataFrame:
	"""
	Returns a DataFrame compatible with your LSTM pipeline:
	  required: date, store_id, sku_id, units_sold
	  optional (if available/derivable): price, promo_flag, on_hand, day_of_week, month, lead_time_days

	For this Kaggle dataset (grocery-inventory):
	  - store_id     <- warehouse_location
	  - sku_id       <- sku_id
	  - date         <- last_order_date  (fallback: date_received)
	  - units_sold   <- sales_volume     (proxy for demand)
	  - on_hand      <- stock_quantity
	  - reorder_level / reorder_quantity exist but are not used as features by default
	"""
	zip_path = cfg.RAW_ZIP_PATH
	if not zip_path.exists():
		raise FileNotFoundError(
			f"Put your Kaggle zip at '{zip_path}'. (Inside ml/: data/raw/grocery_inventory.zip)"
		)

	with zipfile.ZipFile(zip_path, "r") as zf:
		csv_name = _pick_csv_from_zip(zf, cfg.CSV_IN_ZIP)
		with zf.open(csv_name) as f:
			df = pd.read_csv(f)

	# normalize column names
	df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

	# ---- Map Kaggle columns -> model columns ----
	# Your dataset columns (from your error):
	# product_name, catagory, supplier_name, warehouse_location, status, sku_id, supplier_id,
	# date_received, last_order_date, expiration_date, stock_quantity, reorder_level, reorder_quantity,
	# price, sales_volume, inventory_turnover_rate, percentage
	rename = {
		"warehouse_location": "store_id",  # if present in other versions
		"store_id": "store_id",
	
		"product_id": "sku_id",            # <-- THIS fixes your error
		"sku_id": "sku_id",
	
		"units_sold": "units_sold",
		"sales_volume": "units_sold",
	
		"on_hand": "on_hand",
		"stock_quantity": "on_hand",
	
		"date": "date",
		"last_order_date": "date",
	
		"date_received": "date_received",
	
		"unit_price": "price",             # <-- your file uses unit_price
		"price": "price",
	}
	df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

	required_after = ["store_id", "sku_id", "units_sold", "date"]
	missing = [c for c in required_after if c not in df.columns]
	if missing:
		raise ValueError(
			f"Missing required columns after mapping: {missing}\n"
			f"Available columns: {list(df.columns)}"
		)

	# ---- Types ----
	df["store_id"] = df["store_id"].astype(str)
	df["sku_id"] = df["sku_id"].astype(str)

	df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce").fillna(0.0)
	df["units_sold"] = df["units_sold"].clip(lower=0)

	df["on_hand"] = pd.to_numeric(df["on_hand"], errors="coerce").fillna(0.0) if "on_hand" in df.columns else 0.0
	if "price" in df.columns:
		df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)

	df["date"] = pd.to_datetime(df["date"], errors="coerce")
	if "date_received" in df.columns:
		df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")

	# Drop rows without a usable date anchor
	df = df.dropna(subset=["date"])

	# ---- Add required calendar features ----
	df["day_of_week"] = df["date"].dt.dayofweek.astype(int)
	df["month"] = df["date"].dt.month.astype(int)

	# ---- Lead time ----
	# This dataset doesn't truly encode supplier lead time; we provide a default.
	df["lead_time_days"] = cfg.DEFAULT_LEAD_TIME_DAYS

	# promo_flag not present in your columns -> default 0
	df["promo_flag"] = 0

	# If you are NOT expanding, return snapshot-style DF (LSTM may not train well)
	if not cfg.EXPAND_TO_DAILY_SERIES:
		out_cols = ["date", "store_id", "sku_id", "units_sold", "on_hand", "price", "promo_flag", "day_of_week", "month", "lead_time_days"]
		out_cols = [c for c in out_cols if c in df.columns]
		return df[out_cols].sort_values(["store_id", "sku_id", "date"]).reset_index(drop=True)

	# ---- Expand each SKU/store into daily history (synthetic) ----
	# We spread units_sold across days between date_received and date (last_order_date).
	rows = []
	for _, r in df.iterrows():
		end = r["date"]

		start = None
		if "date_received" in df.columns and pd.notna(r.get("date_received")):
			start = r["date_received"]

		# fallback window if start is missing/bad
		if start is None or start > end:
			start = end - pd.Timedelta(days=cfg.FALLBACK_WINDOW_DAYS)

		# create daily range inclusive
		days = pd.date_range(start=start.normalize(), end=end.normalize(), freq="D")
		if len(days) == 0:
			continue

		# distribute total sales_volume uniformly (simple synthetic assumption)
		daily_units = float(r["units_sold"]) / float(len(days))

		for d in days:
			rows.append({
				"date": d,
				"store_id": r["store_id"],
				"sku_id": r["sku_id"],
				"units_sold": daily_units,
				"on_hand": float(r["on_hand"]) if "on_hand" in df.columns else 0.0,
				"price": float(r["price"]) if "price" in df.columns else 0.0,
				"promo_flag": 0,
				"day_of_week": int(d.dayofweek),
				"month": int(d.month),
				"lead_time_days": float(cfg.DEFAULT_LEAD_TIME_DAYS),
			})

	out = pd.DataFrame(rows)
	out = out.sort_values(["store_id", "sku_id", "date"]).reset_index(drop=True)
	return out
