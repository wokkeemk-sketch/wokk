#!/usr/bin/env python3
"""CLI entrypoint: fetch data, evaluate indicators, print/export signals.

This tool only reads market data and prints signals. It never places
trades or touches brokerage/exchange accounts.
"""

import argparse
import sys

import yaml

from signals.data import fetch_history
from signals.report import print_report, write_csv
from signals.strategy import evaluate


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate rule-based technical trading signals.")
    parser.add_argument("--tickers", nargs="+", help="Override the watchlist, e.g. --tickers AAPL MSFT")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--csv", help="Optional path to write results as CSV")
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
        print("No signals generated.", file=sys.stderr)
        return 1

    print_report(results)
    if args.csv:
        write_csv(results, args.csv)
        print(f"Wrote {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
