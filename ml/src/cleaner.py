import re
import pandas as pd


class DataCleaner:

    REQUIRED_COLUMNS = {
        "date",
        "store_id",
        "product_id",
        "inventory_level",
        "units_sold",
        "units_ordered",
        "price",
        "discount",
        "holiday_promotion",
        "competitor_pricing",
        "seasonality",
    }

    def _normalize_column(self, col: str) -> str:
        """
        Convert:
          'Holiday/Promotion' -> 'holiday_promotion'
          'Units Sold'        -> 'units_sold'
        """
        col = col.strip().lower()
        col = re.sub(r"[^a-z0-9]+", "_", col) 
        col = re.sub(r"_+", "_", col)           
        return col.strip("_")

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df.columns = [self._normalize_column(c) for c in df.columns]

        df["date"] = pd.to_datetime(df["date"], errors="raise")

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise KeyError(
                f"Missing required columns: {sorted(missing)}\n"
                f"Available columns: {sorted(df.columns)}"
            )

        df = df.sort_values(["product_id", "store_id", "date"])

        return df
