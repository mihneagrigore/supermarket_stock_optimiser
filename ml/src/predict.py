from __future__ import annotations

import numpy as np
import pandas as pd
import tensorflow as tf

from src.config import Config
from src.features import load_preprocess
from EMILIA import get_clean_dataframe  # optional use here

def compute_rop(daily_mean: float, daily_std: float, lead_time_days: float, z: float) -> float:
    lead_time_days = max(1.0, float(lead_time_days))
    mu_lt = daily_mean * lead_time_days
    sigma_lt = daily_std * np.sqrt(lead_time_days)
    return float(mu_lt + z * sigma_lt)

def compute_eoq(annual_demand: float, order_cost: float, hold_cost: float) -> float:
    annual_demand = max(0.0, float(annual_demand))
    order_cost = max(1e-9, float(order_cost))
    hold_cost = max(1e-9, float(hold_cost))
    return float(np.sqrt((2.0 * annual_demand * order_cost) / hold_cost))

def build_last_window(cfg: Config, bundle, series_df: pd.DataFrame) -> np.ndarray:
    series_df = series_df.sort_values(cfg.COL_DATE)
    feat_df = series_df[bundle.feature_cols].astype("float32")
    if len(feat_df) < bundle.lookback:
        raise ValueError("Not enough history to build a lookback window.")
    feats = bundle.scaler.transform(feat_df.to_numpy())
    window = feats[-bundle.lookback:, :]
    return window[None, :, :].astype("float32")

def recommend_for_series(cfg: Config, model, bundle, series_df: pd.DataFrame) -> dict:
    window = build_last_window(cfg, bundle, series_df)
    horizon_demand = float(model.predict(window, verbose=0).reshape(-1)[0])

    daily_mean = max(0.0, horizon_demand / cfg.HORIZON)

    recent = series_df.sort_values(cfg.COL_DATE)[cfg.COL_DEMAND].astype("float32").to_numpy()
    tail = recent[-max(30, cfg.LOOKBACK):]
    daily_std = float(np.std(tail)) if len(tail) > 1 else 0.0

    lt = float(series_df[cfg.COL_LEAD_TIME_DAYS].iloc[-1]) if cfg.COL_LEAD_TIME_DAYS in series_df.columns else float(cfg.DEFAULT_LEAD_TIME_DAYS)
    if not np.isfinite(lt) or lt <= 0:
        lt = float(cfg.DEFAULT_LEAD_TIME_DAYS)

    rop = compute_rop(daily_mean, daily_std, lt, cfg.SERVICE_LEVEL_Z)

    on_hand = None
    if "on_hand" in series_df.columns:
        v = float(series_df["on_hand"].iloc[-1])
        on_hand = v if np.isfinite(v) else None

    order_cost = float(series_df[cfg.COL_ORDER_COST].iloc[-1]) if cfg.COL_ORDER_COST in series_df.columns else cfg.DEFAULT_ORDER_COST
    hold_cost = float(series_df[cfg.COL_HOLD_COST].iloc[-1]) if cfg.COL_HOLD_COST in series_df.columns else cfg.DEFAULT_HOLD_COST

    annual_demand = daily_mean * 365.0
    eoq = compute_eoq(annual_demand, order_cost, hold_cost)

    if on_hand is None:
        reorder_qty = eoq
        note = "No on_hand available; returning EOQ as suggested lot size."
    else:
        review_buffer_days = 7.0
        order_up_to = rop + daily_mean * review_buffer_days
        reorder_qty = max(0.0, order_up_to - on_hand)
        note = "Order-up-to policy (ROP + buffer) minus on_hand."

    return {
        "forecast_horizon_demand": horizon_demand,
        "daily_mean_est": daily_mean,
        "daily_std_est": daily_std,
        "lead_time_days": lt,
        "reorder_point_units": rop,
        "reorder_quantity_units": float(reorder_qty),
        "note": note,
    }

def main():
    cfg = Config()
    model = tf.keras.models.load_model(cfg.MODEL_PATH)
    bundle = load_preprocess(cfg.PREPROCESS_PATH)

    df = get_clean_dataframe()

    # Example: choose one series (replace with real ids)
    store_id = df[cfg.COL_STORE].iloc[0]
    sku_id = df[cfg.COL_SKU].iloc[0]
    series_df = df[(df[cfg.COL_STORE] == store_id) & (df[cfg.COL_SKU] == sku_id)].copy()

    rec = recommend_for_series(cfg, model, bundle, series_df)
    print(f"Store={store_id} SKU={sku_id}")
    for k, v in rec.items():
        print(f"{k}: {v}")
        

if __name__ == "__main__":
    main()
