from __future__ import annotations

import tensorflow as tf
import pickle
from pathlib import Path

from src.config import Config
from src.model import build_feedforward_model, enable_memory_growth
import sys
sys.path.append(str(Path(__file__).parent.parent))
from data_prep import load_data, clean_data, engineer_features, prepare_training_data, save_scaler


def main():
    """Main training pipeline for feedforward neural network."""
    
    # Load configuration
    cfg = Config()
    cfg.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("FEEDFORWARD NEURAL NETWORK TRAINING")
    print("="*70)
    
    # Enable GPU memory growth
    enable_memory_growth()
    
    # Step 1: Load data
    print("\n[1/5] Loading data...")
    df = load_data(cfg.DATA_PATH)
    
    # Step 2: Clean data
    print("\n[2/5] Cleaning data...")
    df = clean_data(df)
    
    # Step 3: Engineer features
    print("\n[3/5] Engineering features...")
    df = engineer_features(df)
    
    # Step 4: Prepare training data
    print("\n[4/5] Preparing training data...")
    X_train, X_test, y_train, y_test, scaler = prepare_training_data(
        df, 
        cfg.FEATURE_COLUMNS, 
        cfg.TARGET_COLUMN,
        test_size=cfg.TEST_SIZE,
        random_state=cfg.RANDOM_STATE
    )
    
    # Save scaler
    save_scaler(scaler, cfg.SCALER_PATH)
    
    # Build model
    print("\n[5/5] Building and training model...")
    model = build_feedforward_model(
        n_features=len(cfg.FEATURE_COLUMNS),
        lr=cfg.LEARNING_RATE,
        dropout_rate_1=cfg.DROPOUT_RATE_1,
        dropout_rate_2=cfg.DROPOUT_RATE_2
    )
    
    # Print model summary
    print("\nModel Architecture:")
    model.summary()
    
    # Define callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_mae',
            patience=cfg.EARLY_STOPPING_PATIENCE,
            restore_best_weights=True,
            verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_mae',
            factor=cfg.REDUCE_LR_FACTOR,
            patience=cfg.REDUCE_LR_PATIENCE,
            min_lr=cfg.MIN_LR,
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(cfg.BEST_PATH),
            monitor='val_mae',
            save_best_only=True,
            verbose=1
        )
    ]
    
    # Train model
    print(f"\nTraining for {cfg.EPOCHS} epochs (batch_size={cfg.BATCH_SIZE})...")
    print("="*70)
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=cfg.EPOCHS,
        batch_size=cfg.BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save final model
    model.save(cfg.MODEL_PATH)
    print(f"\n✓ Saved final model: {cfg.MODEL_PATH}")
    print(f"✓ Saved best checkpoint: {cfg.BEST_PATH}")
    
    # Save training history
    with open(cfg.HISTORY_PATH, 'wb') as f:
        pickle.dump(history.history, f)
    print(f"✓ Saved training history: {cfg.HISTORY_PATH}")
    
    # Evaluate on test set
    print("\n" + "="*70)
    print("FINAL EVALUATION")
    print("="*70)
    
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Set Performance:")
    print(f"  MAE (Mean Absolute Error): {test_mae:.2f}")
    print(f"  Loss: {test_loss:.2f}")
    
    # Training set performance
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    print(f"\nTraining Set Performance:")
    print(f"  MAE: {train_mae:.2f}")
    print(f"  Loss: {train_loss:.2f}")
    
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
