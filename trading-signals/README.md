# Trading Signals

Rule-based technical-analysis signal generator for US stocks/ETFs. **Reads
market data and prints signals only — it never places trades or touches a
brokerage account.**

> **Not financial advice.** These are simple, transparent heuristics based on
> well-known technical indicators. They are not backtested for profitability
> and should not be the sole basis for any investment decision.

## What it does

For each ticker in your watchlist, it pulls recent daily price history
(via Yahoo Finance) and evaluates four indicators:

- **RSI(14)** — oversold (<30) / overbought (>70)
- **MACD(12,26,9)** — bullish/bearish crossover of the MACD and signal lines
- **EMA crossover (20/50)** — fast EMA crossing above/below the slow EMA
- **Bollinger Bands(20, 2σ)** — price touching the lower/upper band

Each indicator casts one vote (BUY / SELL / NEUTRAL). The composite signal
for a ticker is BUY or SELL only if that side has a strict majority of the
votes; otherwise it's HOLD. The full per-indicator breakdown is always shown
so you can see *why*.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Uses the watchlist in config.yaml
python main.py

# Or specify tickers directly
python main.py --tickers AAPL MSFT NVDA

# Export the breakdown to CSV
python main.py --tickers AAPL MSFT --csv signals.csv
```

Edit `config.yaml` to change the default watchlist, lookback period, or any
indicator's parameters (RSI thresholds, MACD/EMA periods, Bollinger
band width).

## Project layout

```
main.py                  CLI entrypoint
config.yaml               watchlist + indicator parameters
signals/data.py           Yahoo Finance data fetching
signals/indicators.py     RSI / MACD / EMA / Bollinger Band math
signals/strategy.py       combines indicators into a per-ticker signal
signals/report.py         console + CSV output
tests/test_indicators.py  unit tests against synthetic price data
```

## Testing

```bash
pytest tests/
```

## Extending

- **Different indicators or weights**: edit `signals/strategy.py` — each
  indicator just needs to append an `IndicatorVote`.
- **Scheduling**: run `main.py` from cron/Task Scheduler for a daily digest,
  or pipe `--csv` output into your own notifier (email/Slack/Telegram).
- **Automated execution**: deliberately not included here. If you later want
  the tool to place real orders, that requires broker API credentials and
  should include hard safety limits (position size caps, stop-loss, a kill
  switch, and paper-trading validation first) — treat it as a separate,
  carefully-reviewed piece of work, not an extension of this script.
