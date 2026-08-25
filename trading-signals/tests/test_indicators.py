import numpy as np
import pandas as pd

from signals.indicators import bollinger_bands, ema, macd, rsi
from signals.strategy import evaluate


def _synthetic_close(n=120, seed=0):
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.1, scale=1.0, size=n)
    return pd.Series(100 + np.cumsum(steps))


def test_rsi_bounds():
    close = _synthetic_close()
    values = rsi(close, period=14).dropna()
    assert (values >= 0).all() and (values <= 100).all()


def test_rsi_extremes():
    rising = pd.Series(np.arange(1, 30, dtype=float))
    assert rsi(rising, period=14).iloc[-1] > 90

    falling = pd.Series(np.arange(30, 1, -1, dtype=float))
    assert rsi(falling, period=14).iloc[-1] < 10


def test_macd_shape():
    close = _synthetic_close()
    result = macd(close, fast=12, slow=26, signal=9)
    assert list(result.columns) == ["macd", "signal", "histogram"]
    assert len(result) == len(close)
    np.testing.assert_allclose(result["histogram"], result["macd"] - result["signal"])


def test_ema_converges_to_price_on_flat_series():
    flat = pd.Series([50.0] * 60)
    assert ema(flat, period=20).iloc[-1] == 50.0


def test_bollinger_bands_ordering():
    close = _synthetic_close()
    bands = bollinger_bands(close, period=20, num_std=2).dropna()
    assert (bands["upper"] >= bands["middle"]).all()
    assert (bands["middle"] >= bands["lower"]).all()


def test_evaluate_returns_signal_for_each_indicator():
    close = _synthetic_close(n=100)
    df = pd.DataFrame({"Close": close})
    params = {
        "rsi": {"period": 14, "oversold": 30, "overbought": 70},
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "ema_crossover": {"fast": 20, "slow": 50},
        "bollinger": {"period": 20, "num_std": 2},
    }
    result = evaluate(df, "TEST", params)
    assert result.ticker == "TEST"
    assert result.composite in {"BUY", "SELL", "HOLD"}
    assert {v.name for v in result.votes} == {"RSI", "MACD", "EMA Crossover", "Bollinger Bands"}
