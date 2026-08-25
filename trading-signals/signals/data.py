"""Historical OHLCV data fetching via Yahoo Finance."""

import pandas as pd
import yfinance as yf


def fetch_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV history for a single ticker. Raises ValueError if no data is returned."""
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"No data returned for ticker '{ticker}' - check the symbol is valid")
    return df
