from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import pickle

@dataclass
class PreprocessBundle:
    feature_cols: list[str]
    scaler: StandardScaler
    lookback: int
    horizon: int

def _ensure_sorted(df: pd.DataFrame, store_col: str, sku_col: str, date_col: str) -> pd.DataFrame:
    return df.sort_values([store_col, sku_col, date_col]).reset_index(drop=True)

def build_feature_columns(cfg, df: pd.DataFrame) -> list[str]:
    cols = [cfg.COL_DEMAND]  # always include demand history
    for c in cfg.EXTRA_NUMERIC_FEATURES:
        if c in df.columns:
            cols.append(c)
    return cols

def time_split_by_series(cfg, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = _ensure_sorted(df, cfg.COL_STORE, cfg.COL_SKU, cfg.COL_DATE)
    train_parts, val_parts = [], []
    frac = cfg.VAL_SPLIT_TIME_FRACTION

    for _, g in df.groupby([cfg.COL_STORE, cfg.COL_SKU], sort=False):
        g = g.sort_values(cfg.COL_DATE)
        if len(g) < (cfg.LOOKBACK + cfg.HORIZON + 5):
            continue
        cut = int(np.floor(len(g) * (1.0 - frac)))
        train_parts.append(g.iloc[:cut])
        val_parts.append(g.iloc[cut:])

    if not train_parts:
        raise ValueError("No series were long enough after splitting. Need more history per SKU/store.")
    return pd.concat(train_parts).reset_index(drop=True), pd.concat(val_parts).reset_index(drop=True)

def make_supervised(cfg, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, PreprocessBundle]:
    """
    X: (n_samples, lookback, n_features)
    y: (n_samples,) where y = sum demand over next horizon
    """
    df = _ensure_sorted(df, cfg.COL_STORE, cfg.COL_SKU, cfg.COL_DATE)

    required = [cfg.COL_DATE, cfg.COL_STORE, cfg.COL_SKU, cfg.COL_DEMAND]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    feature_cols = build_feature_columns(cfg, df)
    scaler = StandardScaler()

    feat_matrix = df[feature_cols].astype("float32").to_numpy()
    scaler.fit(feat_matrix)

    X_list, y_list = [], []

    for _, g in df.groupby([cfg.COL_STORE, cfg.COL_SKU], sort=False):
        g = g.sort_values(cfg.COL_DATE)
        feats = scaler.transform(g[feature_cols].astype("float32").to_numpy())
        demand = g[cfg.COL_DEMAND].astype("float32").to_numpy()

        L, H = cfg.LOOKBACK, cfg.HORIZON
        if len(g) < L + H:
            continue

        for t in range(L, len(g) - H + 1):
            X_list.append(feats[t - L:t, :])
            y_list.append(float(demand[t:t + H].sum()))

    if not X_list:
        raise ValueError("No training samples were created. Check LOOKBACK/HORIZON and series lengths.")

    X = np.stack(X_list).astype("float32")
    y = np.array(y_list, dtype="float32")

    bundle = PreprocessBundle(
        feature_cols=feature_cols,
        scaler=scaler,
        lookback=cfg.LOOKBACK,
        horizon=cfg.HORIZON
    )
    return X, y, bundle

def save_preprocess(bundle: PreprocessBundle, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(bundle, f)

def load_preprocess(path) -> PreprocessBundle:
    with open(path, "rb") as f:
        return pickle.load(f)
