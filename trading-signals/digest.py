#!/usr/bin/env python3
"""Daily digest: generate signals and email the report.

Intended to be run on a schedule (cron / Task Scheduler) on a machine with
normal internet access - not from a restricted sandbox. Reads SMTP
credentials from environment variables; see .env.example.
"""

import argparse
import sys

from dotenv import load_dotenv

from signals.config import load_config
from signals.data import fetch_history
from signals.notify import send_email
from signals.report import format_report_text
from signals.strategy import evaluate


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate signals and email the daily digest.")
    parser.add_argument("--tickers", nargs="+", help="Override the watchlist, e.g. --tickers AAPL MSFT")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    tickers = args.tickers or config["watchlist"]
    period = config["lookback_period"]
    interval = config["interval"]
    indicator_params = config["indicators"]

    results = []
    for ticker in tickers:
        try:
            df = fetch_history(ticker, period=period, interval=interval)
            results.append(evaluate(df, ticker, indicator_params))
        except Exception as e:
            print(f"Skipping {ticker}: {e}", file=sys.stderr)

    if not results:
        print("No signals generated - not sending an email.", file=sys.stderr)
        return 1

    body = format_report_text(results)
    print(body)  # so cron logs capture it too
    send_email(subject="Trading Signals Digest", body=body)
    print("Digest emailed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
