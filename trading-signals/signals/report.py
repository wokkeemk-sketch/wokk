"""Console and CSV reporting for ticker signals."""

import csv
from datetime import datetime, timezone

from signals.strategy import TickerSignal

_COLOR = {"BUY": "\033[32m", "SELL": "\033[31m", "HOLD": "\033[33m", "RESET": "\033[0m"}


def print_report(results: list[TickerSignal]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\nTrading Signals Report — {now}")
    print("Not financial advice. Rule-based technical signals only.\n")

    for r in results:
        color = _COLOR.get(r.composite, "")
        reset = _COLOR["RESET"]
        print(f"{r.ticker:<6} ${r.price:>9.2f}  {color}{r.composite:<5}{reset}")
        for vote in r.votes:
            print(f"    {vote.name:<16} {vote.vote:<8} {vote.detail}")
        print()


def write_csv(results: list[TickerSignal], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "price", "composite_signal", "indicator", "vote", "detail"])
        for r in results:
            for vote in r.votes:
                writer.writerow([r.ticker, f"{r.price:.2f}", r.composite, vote.name, vote.vote, vote.detail])
