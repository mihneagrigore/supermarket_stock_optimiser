from __future__ import annotations

import tensorflow as tf


def enable_memory_growth():
    """Enable GPU memory growth to avoid allocation issues."""
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)


def build_feedforward_model(n_features: int, lr: float, dropout_rate_1: float = 0.3, dropout_rate_2: float = 0.2) -> tf.keras.Model:
    """
    Build feedforward neural network (Dense/MLP) for inventory reorder prediction.
    
    Architecture:
        Input(n_features) 
        -> Dense(128, relu) -> BatchNorm -> Dropout(0.3)
        -> Dense(64, relu) -> BatchNorm -> Dropout(0.3)
        -> Dense(32, relu) -> Dropout(0.2)
        -> Dense(1, relu)  # ReLU to enforce non-negative predictions
    
    Args:
        n_features: Number of input features
        lr: Learning rate for Adam optimizer
        dropout_rate_1: Dropout rate for first two layers
        dropout_rate_2: Dropout rate for third layer
    
    Returns:
        Compiled Keras model
    """
    inputs = tf.keras.Input(shape=(n_features,), name='features')
    
    # First hidden layer
    x = tf.keras.layers.Dense(128, activation='relu', name='dense_1')(inputs)
    x = tf.keras.layers.BatchNormalization(name='bn_1')(x)
    x = tf.keras.layers.Dropout(dropout_rate_1, name='dropout_1')(x)
    
    # Second hidden layer
    x = tf.keras.layers.Dense(64, activation='relu', name='dense_2')(x)
    x = tf.keras.layers.BatchNormalization(name='bn_2')(x)
    x = tf.keras.layers.Dropout(dropout_rate_1, name='dropout_2')(x)
    
    # Third hidden layer
    x = tf.keras.layers.Dense(32, activation='relu', name='dense_3')(x)
    x = tf.keras.layers.Dropout(dropout_rate_2, name='dropout_3')(x)
    
    # Output layer (ReLU to enforce non-negative predictions)
    outputs = tf.keras.layers.Dense(1, activation='relu', name='reorder_qty')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name='feedforward_reorder')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss='mae',
        metrics=[tf.keras.metrics.MeanAbsoluteError(name='mae')]
    )
    
    return model
