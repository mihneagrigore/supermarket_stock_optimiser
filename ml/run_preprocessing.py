import pandas as pd
from data.downloader import KaggleDownloader
from src.pipeline import PreprocessingPipeline
from config import RAW_DATA_PATH

# Download
downloader = KaggleDownloader()
downloader.download()

df = pd.read_csv(f"{RAW_DATA_PATH}/retail_store_inventory.csv")

# Preprocess
pipeline = PreprocessingPipeline()
processed_df = pipeline.run(df)
