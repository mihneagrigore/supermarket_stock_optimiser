import pandas as pd
from data.downloader import KaggleDownloader
from src.pipeline import PreprocessingPipeline
from config import RAW_DATA_PATH

# CONFIG
TEST_RATIO = 0.2
DATE_COL = "date"
TARGET_COL = "units_sold"


# Download
downloader = KaggleDownloader()
downloader.download()

# Load raw data
df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")

# Preprocess
pipeline = PreprocessingPipeline()
processed_df = pipeline.run(df)

processed_df = processed_df.sort_values(DATE_COL).reset_index(drop=True)

split_idx = int(len(processed_df) * (1 - TEST_RATIO))

# Split
train_df = processed_df.iloc[:split_idx].copy()
test_df = processed_df.iloc[split_idx:].copy()

X_train = train_df.drop(columns=[DATE_COL, TARGET_COL])
y_train = train_df[TARGET_COL]

X_test = test_df.drop(columns=[DATE_COL, TARGET_COL])
y_test = test_df[TARGET_COL]


print("\n================ SPLIT SUMMARY ================\n")
print(f"Total rows    : {len(processed_df)}")
print(f"Train rows    : {len(train_df)}")
print(f"Test rows     : {len(test_df)}")

print("\nTraining period:")
print(train_df[DATE_COL].min(), "→", train_df[DATE_COL].max())

print("\nTesting period:")
print(test_df[DATE_COL].min(), "→", test_df[DATE_COL].max())

print("\nFeature columns:")
print(list(X_train.columns))
