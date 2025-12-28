import tensorflow as tf

def enable_memory_growth():
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)

def build_lstm_model(n_features: int, lookback: int, lr: float) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(lookback, n_features))
    x = tf.keras.layers.LSTM(128, return_sequences=True)(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.LSTM(64)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1)(x)  # horizon demand

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss=tf.keras.losses.Huber(delta=1.0),
        metrics=[tf.keras.metrics.MeanAbsoluteError(name="mae")]
    )
    return model
