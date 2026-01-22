import pandas as pd
import numpy as np
from src import preprocessing as pp

def test_clean_transaction_dates_and_sanitize_amounts():
    df = pd.DataFrame(
        {
            "Account_Number": ["A", "A", "B", "C"],
            "Transaction_Date": ["2025-01-01", "not a date", "1800-01-01", None],
            "Transaction_Amount": ["100.0", "abc", None, "50"],
        }
    )

    df2 = pp.clean_transaction_dates(df, date_col="Transaction_Date", min_date=pd.Timestamp("1970-01-01"))
    assert "_days_since_date" in df2.columns
    assert df2["_days_since_date"].dtype == np.int32

    df3 = pp.sanitize_amounts(df2, amount_col="Transaction_Amount", fill_value=0.0)
    assert df3["Transaction_Amount"].dtype == float
    assert df3["Transaction_Amount"].sum() == 150.0
