import pandas as pd


class FeatureEngineer:
    def add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["day_of_week"] = df["date"].dt.weekday
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["month"] = df["date"].dt.month
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        return df

    def add_lag_features(self, df: pd.DataFrame, group_col: str = "product_id") -> pd.DataFrame:
        """Add lag and rolling features per product to prevent cross-product leakage."""
        lags = [1, 7, 14, 28]
        for lag in lags:
            df[f"units_sold_lag_{lag}"] = df.groupby(group_col)["units_sold"].shift(lag)

        # Rolling means within each product group
        df["units_sold_roll_mean_7"] = (
            df.groupby(group_col)["units_sold"]
            .transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
        )
        df["units_sold_roll_mean_14"] = (
            df.groupby(group_col)["units_sold"]
            .transform(lambda x: x.shift(1).rolling(14, min_periods=1).mean())
        )

        return df
