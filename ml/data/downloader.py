import os
import zipfile
from config import KAGGLE_USERNAME, KAGGLE_KEY, DATASET_NAME, RAW_DATA_PATH


class KaggleDownloader:
    def __init__(self):
        os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
        os.environ["KAGGLE_KEY"] = KAGGLE_KEY
        os.makedirs(RAW_DATA_PATH, exist_ok=True)

    def download(self):
        os.system(
            f"kaggle datasets download -d {DATASET_NAME} "
            f"-p {RAW_DATA_PATH} --unzip"
        )
        print(f"Dataset downloaded and extracted to {RAW_DATA_PATH}")