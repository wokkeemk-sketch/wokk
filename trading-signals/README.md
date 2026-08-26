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

## Daily email digest

`digest.py` generates the same report and emails it to you, via SMTP (works
with Gmail using an app password). Meant to run on a schedule from a machine
with normal internet access.

1. Turn on 2-Step Verification on your Google account, then create an app
   password at https://myaccount.google.com/apppasswords.
2. `cp .env.example .env` and fill in `SMTP_USERNAME` / `SMTP_PASSWORD`
   (the app password, not your normal login password) / `DIGEST_TO`.
   `.env` is gitignored — never commit real credentials.
3. Test it manually:

   ```bash
   python digest.py
   ```

4. Schedule it:

   **macOS/Linux (cron)** — `crontab -e`, then add (7am daily; adjust the path):

   ```
   0 7 * * * cd /path/to/trading-signals && /usr/bin/python3 digest.py >> digest.log 2>&1
   ```

   **Windows (Task Scheduler)** — create a daily trigger that runs:

   ```
   python.exe C:\path\to\trading-signals\digest.py
   ```

   with "Start in" set to the `trading-signals` folder.

## Project layout

```
main.py                  interactive CLI entrypoint
digest.py                 scheduled entrypoint — generates + emails the report
config.yaml               watchlist + indicator parameters
.env.example               SMTP credential template (copy to .env)
signals/data.py           Yahoo Finance data fetching
signals/indicators.py     RSI / MACD / EMA / Bollinger Band math
signals/strategy.py       combines indicators into a per-ticker signal
signals/report.py         console + plain-text + CSV output
signals/notify.py         SMTP email delivery
tests/test_indicators.py  unit tests against synthetic price data
```

## Testing

```bash
pytest tests/
```

## Extending

- **Different indicators or weights**: edit `signals/strategy.py` — each
  indicator just needs to append an `IndicatorVote`.
- **Other delivery channels**: swap `signals/notify.py` for a Telegram bot
  or Slack webhook call — `digest.py` just needs `format_report_text(results)`
  handed to whatever you use to send it.
- **Automated execution**: deliberately not included here. If you later want
  the tool to place real orders, that requires broker API credentials and
  should include hard safety limits (position size caps, stop-loss, a kill
  switch, and paper-trading validation first) — treat it as a separate,
  carefully-reviewed piece of work, not an extension of this script.
