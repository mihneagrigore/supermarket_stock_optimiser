from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tensorflow as tf
import numpy as np

from src.config import Config
from src.model import build_lstm_model, enable_memory_growth

try:
    from run_preprocessing import load_preprocessed_data
    USE_RUN_PREPROCESSING = True
except ImportError:
    from data_prep import clean_data, load_data
    USE_RUN_PREPROCESSING = False

def main():
    cfg = Config()
    cfg.MODEL_DIR.mkdir(parents=True, exist_ok=True)

    enable_memory_growth()

    if USE_RUN_PREPROCESSING:
        print("Loading preprocessed data from run_preprocessing.py...")
        X_train, y_train, X_test, y_test = load_preprocessed_data()
        print(f"Loaded shapes: X_train={X_train.shape}, y_train={y_train.shape}")
        # Data already has correct shape (samples, lookback, features) from run_preprocessing
    else:
        print("Using data_prep.py preprocessing...")
        df = load_data()
        X_train, y_train, X_test, y_test = clean_data(
            df, 
            lookback=cfg.LOOKBACK, 
            horizon=cfg.HORIZON
        )

    model = build_lstm_model(
        n_features=X_train.shape[-1],
        lookback=cfg.LOOKBACK,
        lr=cfg.LEARNING_RATE
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_mae", patience=50, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_mae", factor=0.5, patience=50, min_lr=1e-7, verbose=1),
        tf.keras.callbacks.ModelCheckpoint(filepath=str(cfg.BEST_PATH), monitor="val_mae", save_best_only=True),
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=cfg.EPOCHS,
        batch_size=cfg.BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )

    model.save(cfg.MODEL_PATH)

    print(f"Saved best checkpoint: {cfg.BEST_PATH}")
    print(f"Saved model: {cfg.MODEL_PATH}")

if __name__ == "__main__":
    main()
