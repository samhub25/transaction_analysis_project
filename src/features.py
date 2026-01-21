"""
Vectorized feature-engineering helpers.

Primary functions:
- daily_and_monthly_aggregates: groupby aggregates per account and day/month.
- compute_velocity_features: compute velocity ratios and flags safely.
"""
from typing import Tuple
import pandas as pd
import numpy as np


def daily_and_monthly_aggregates(
    df: pd.DataFrame,
    account_col: str = "Account_Number",
    date_col: str = "Transaction_Date",
    amount_col: str = "Transaction_Amount",
) -> pd.DataFrame:
    """
    Return aggregated DataFrame with daily totals and monthly baseline.
    - Expects date_col to be datetime (if not, caller should parse).
    """
    df = df.copy()
    if date_col not in df.columns:
        raise KeyError(f"{date_col} not in dataframe")

    # Daily totals per account
    df["txn_date_only"] = df[date_col].dt.floor("D")
    daily = (
        df.groupby([account_col, "txn_date_only"], as_index=False)[amount_col]
        .sum()
        .rename(columns={amount_col: "daily_amount"})
    )

    # Monthly baseline per account (mean monthly amount)
    df["txn_month"] = df[date_col].dt.to_period("M")
    monthly = (
        df.groupby([account_col, "txn_month"], as_index=False)[amount_col]
        .sum()
        .groupby(account_col, as_index=False)["amount"]
        .mean()
        .rename(columns={"amount": "monthly_baseline"})
    )

    # The monthly groupby above uses a two-stage step; simpler alternative:
    monthly2 = (
        df.groupby([account_col, "txn_month"], as_index=False)[amount_col]
        .sum()
        .groupby(account_col, as_index=False)[amount_col]
        .mean()
        .rename(columns={amount_col: "monthly_baseline"})
    )

    # Merge baseline into daily
    out = daily.merge(monthly2, on=account_col, how="left")
    out["monthly_baseline"] = out["monthly_baseline"].fillna(0.0)

    return out


def compute_velocity_features(
    daily_df: pd.DataFrame,
    baseline_col: str = "monthly_baseline",
    daily_amount_col: str = "daily_amount",
    velocity_col_name: str = "Daily_Velocity_Ratio",
    flag_col_name: str = "Velocity_Flag_Combined",
    threshold: float = 3.0,
) -> pd.DataFrame:
    """
    Compute velocity ratio = daily_amount / (baseline / avg_days_in_month)
    - Baseline is monthly total; convert to average daily baseline.
    - Safe against divide-by-zero.
    - Adds velocity ratio and flag columns.
    """
    df = daily_df.copy()

    # Convert monthly baseline (total per month) -> daily average estimate
    days_per_month = 30.0
    df["_daily_baseline_est"] = df[baseline_col] / days_per_month

    # Avoid division by zero: if baseline is zero, set baseline_est to small epsilon
    eps = 1e-9
    df["_daily_baseline_est"] = df["_daily_baseline_est"].replace(0, eps)

    df[velocity_col_name] = df[daily_amount_col] / df["_daily_baseline_est"]

    # Create a combined flag: velocity > threshold
    df[flag_col_name] = (df[velocity_col_name] > threshold).astype(int)

    # Clean temporary
    df = df.drop(columns=["_daily_baseline_est"], errors="ignore")
    return df