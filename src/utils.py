"""
Small utilities: logging setup and simple helpers.
"""
import logging
import pandas as pd


def setup_logging(level: int = logging.INFO):
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s", level=level
    )


def ensure_datetime(
    df: pd.DataFrame, col: str = "Transaction_Date", errors: str = "coerce"
) -> pd.DataFrame:
    """
    Ensure a column is datetime; returns df copy with parsed column.
    """
    df = df.copy()
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors=errors)
    return df