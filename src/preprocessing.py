"""
Robust preprocessing helpers for transaction data.

Functions:
- load_transactions: chunked CSV loader with dtype hints.
- clean_transaction_dates: parse, coerce, clamp dates and compute capped day-deltas.
- sanitize_amounts: convert amounts to numeric safely and fill/flag invalids.
- reduce_memory_usage: downcast numeric dtypes to save memory.
"""
from typing import Optional, Dict, Iterable
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_transactions(
    path: str,
    chunksize: Optional[int] = None,
    dtype: Optional[Dict[str, str]] = None,
    usecols: Optional[Iterable[str]] = None,
):
    """
    Load transactions from CSV. If chunksize is provided, yields DataFrame chunks.
    Use dtype hints to reduce memory.
    """
    if chunksize:
        for chunk in pd.read_csv(path, dtype=dtype, usecols=usecols, chunksize=chunksize):
            yield chunk
    else:
        return pd.read_csv(path, dtype=dtype, usecols=usecols)


def clean_transaction_dates(
    df: pd.DataFrame,
    date_col: str = "Transaction_Date",
    min_date: pd.Timestamp = pd.Timestamp("1970-01-01"),
    max_date: Optional[pd.Timestamp] = None,
    cap_days: int = 1825,
    reference_date_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Parse and sanitize transaction dates.

    - Ensures date_col exists.
    - Converts to datetime with errors='coerce'.
    - Clamps dates to [min_date, max_date].
    - Computes days since last credit/debit (if reference_date_col provided or now).
    - Caps large day deltas at cap_days (default 5 years).
    """
    if max_date is None:
        max_date = pd.Timestamp.now() + pd.Timedelta(days=365)

    if date_col not in df.columns:
        logger.warning("Date column '%s' not found; returning df unchanged", date_col)
        return df

    # Work on a copy to avoid SettingWithCopyWarning
    df = df.copy()

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=False)

    # Clamp to sensible range
    df.loc[df[date_col] < min_date, date_col] = pd.NaT
    df.loc[df[date_col] > max_date, date_col] = pd.NaT

    # If we need "days since" features, use reference_date_col or now
    if reference_date_col and reference_date_col in df.columns:
        ref = pd.to_datetime(df[reference_date_col], errors="coerce")
    else:
        ref = pd.Timestamp.now()

    # Example: Days since each date (useful for some features)
    df["_days_since_date"] = (ref - df[date_col]).dt.days
    # Cap extreme values and fill missing with cap value
    df["_days_since_date"] = df["_days_since_date"].clip(lower=0, upper=cap_days)
    df["_days_since_date"] = df["_days_since_date"].fillna(cap_days).astype(np.int32)

    return df


def sanitize_amounts(
    df: pd.DataFrame, amount_col: str = "Transaction_Amount", fill_value: float = 0.0
) -> pd.DataFrame:
    """
    Ensure transaction amounts are numeric and reasonable.
    - Coerce non-numeric to NaN then fill or flag.
    - Optionally clip to reasonable bounds if domain requires.
    """
    df = df.copy()
    if amount_col not in df.columns:
        logger.warning("Amount column '%s' not found; returning df unchanged", amount_col)
        return df

    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")
    # Replace negative zeros or infinities
    df.loc[~np.isfinite(df[amount_col]), amount_col] = np.nan
    df[amount_col] = df[amount_col].fillna(fill_value).astype(float)
    return df


def reduce_memory_usage(df: pd.DataFrame, int_cast_to: str = "int32") -> pd.DataFrame:
    """
    Downcast numeric columns to reduce memory usage.
    - Downcasts integers and floats where safe.
    - Leaves objects as-is.
    """
    df = df.copy()
    for col in df.select_dtypes(include=["int64", "int32"]).columns:
        try:
            df[col] = pd.to_numeric(df[col], downcast="integer")
        except Exception:
            pass
    for col in df.select_dtypes(include=["float64"]).columns:
        try:
            df[col] = pd.to_numeric(df[col], downcast="float")
        except Exception:
            pass
    return df