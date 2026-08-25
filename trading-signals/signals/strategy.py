"""Combine indicators into a per-ticker signal via simple majority vote.

This is a transparent, rule-based heuristic - not financial advice, and not
backtested for profitability. Each indicator casts one vote (BUY/SELL/NEUTRAL);
the composite signal is whichever side has a majority of the votes, otherwise HOLD.
"""

from dataclasses import dataclass, field

import pandas as pd

from signals.indicators import bollinger_bands, ema, macd, rsi


@dataclass
class IndicatorVote:
    name: str
    vote: str  # "BUY", "SELL", or "NEUTRAL"
    detail: str


@dataclass
class TickerSignal:
    ticker: str
    price: float
    composite: str  # "BUY", "SELL", or "HOLD"
    votes: list = field(default_factory=list)


def evaluate(df: pd.DataFrame, ticker: str, params: dict) -> TickerSignal:
    close = df["Close"]
    price = float(close.iloc[-1])
    votes = []

    rsi_params = params["rsi"]
    rsi_series = rsi(close, rsi_params["period"])
    last_rsi = rsi_series.iloc[-1]
    if pd.notna(last_rsi):
        if last_rsi < rsi_params["oversold"]:
            votes.append(IndicatorVote("RSI", "BUY", f"RSI {last_rsi:.1f} < {rsi_params['oversold']} (oversold)"))
        elif last_rsi > rsi_params["overbought"]:
            votes.append(IndicatorVote("RSI", "SELL", f"RSI {last_rsi:.1f} > {rsi_params['overbought']} (overbought)"))
        else:
            votes.append(IndicatorVote("RSI", "NEUTRAL", f"RSI {last_rsi:.1f}"))

    macd_params = params["macd"]
    macd_df = macd(close, macd_params["fast"], macd_params["slow"], macd_params["signal"])
    macd_now, signal_now = macd_df["macd"].iloc[-1], macd_df["signal"].iloc[-1]
    macd_prev, signal_prev = macd_df["macd"].iloc[-2], macd_df["signal"].iloc[-2]
    if pd.notna(macd_now) and pd.notna(macd_prev):
        crossed_up = macd_prev <= signal_prev and macd_now > signal_now
        crossed_down = macd_prev >= signal_prev and macd_now < signal_now
        if crossed_up:
            votes.append(IndicatorVote("MACD", "BUY", "MACD crossed above signal line"))
        elif crossed_down:
            votes.append(IndicatorVote("MACD", "SELL", "MACD crossed below signal line"))
        else:
            above = "above" if macd_now > signal_now else "below"
            votes.append(IndicatorVote("MACD", "NEUTRAL", f"MACD line {above} signal line, no fresh cross"))

    ema_params = params["ema_crossover"]
    ema_fast = ema(close, ema_params["fast"])
    ema_slow = ema(close, ema_params["slow"])
    fast_now, slow_now = ema_fast.iloc[-1], ema_slow.iloc[-1]
    fast_prev, slow_prev = ema_fast.iloc[-2], ema_slow.iloc[-2]
    if pd.notna(fast_now) and pd.notna(fast_prev):
        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now
        if crossed_up:
            votes.append(IndicatorVote("EMA Crossover", "BUY", f"EMA{ema_params['fast']} crossed above EMA{ema_params['slow']}"))
        elif crossed_down:
            votes.append(IndicatorVote("EMA Crossover", "SELL", f"EMA{ema_params['fast']} crossed below EMA{ema_params['slow']}"))
        else:
            trend = "uptrend" if fast_now > slow_now else "downtrend"
            votes.append(IndicatorVote("EMA Crossover", "NEUTRAL", f"In {trend}, no fresh cross"))

    bb_params = params["bollinger"]
    bb_df = bollinger_bands(close, bb_params["period"], bb_params["num_std"])
    upper, lower = bb_df["upper"].iloc[-1], bb_df["lower"].iloc[-1]
    if pd.notna(upper) and pd.notna(lower):
        if price <= lower:
            votes.append(IndicatorVote("Bollinger Bands", "BUY", f"Price {price:.2f} at/below lower band {lower:.2f}"))
        elif price >= upper:
            votes.append(IndicatorVote("Bollinger Bands", "SELL", f"Price {price:.2f} at/above upper band {upper:.2f}"))
        else:
            votes.append(IndicatorVote("Bollinger Bands", "NEUTRAL", f"Price {price:.2f} within bands [{lower:.2f}, {upper:.2f}]"))

    buy_votes = sum(1 for v in votes if v.vote == "BUY")
    sell_votes = sum(1 for v in votes if v.vote == "SELL")
    majority = len(votes) / 2

    if buy_votes > sell_votes and buy_votes > majority:
        composite = "BUY"
    elif sell_votes > buy_votes and sell_votes > majority:
        composite = "SELL"
    else:
        composite = "HOLD"

    return TickerSignal(ticker=ticker, price=price, composite=composite, votes=votes)
