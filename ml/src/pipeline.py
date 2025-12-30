import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.cleaner import DataCleaner
from src.feature_engineer import FeatureEngineer
from config import PRODUCT_ID


class PreprocessingPipeline:
    def __init__(self):
        self.cleaner = DataCleaner()
        self.fe = FeatureEngineer()

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.cleaner.clean(df)

        # Aggregate by (product_id, date) to preserve per-product time series
        # Sum across stores for each product on each date
        df = (
            df.groupby(["product_id", "date"], as_index=False)
              .agg({
                  "units_sold": "sum",
                  "inventory_level": "sum",
                  "units_ordered": "sum",
                  "price": "mean",
                  "discount": "mean",
                  "holiday_promotion": "max",
                  "seasonality": "first"
              })
        )

        df = df[
            [
                "product_id",
                "date",
                "units_sold",
                "inventory_level",
                "units_ordered",
                "price",
                "discount",
                "holiday_promotion",
                "seasonality"
            ]
        ]

        df = self.fe.add_calendar_features(df)
        df = self.fe.add_lag_features(df)

        df = df.dropna().reset_index(drop=True)

        return df
