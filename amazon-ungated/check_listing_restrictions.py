#!/usr/bin/env python3
"""
Check Amazon listing restrictions (gated/ungated status) for a list of ASINs
using the SP-API Listings Restrictions endpoint.

Input:  a CSV with a header row and at least an "asin" column.
Output: a CSV with restriction status and reasons per ASIN.

Setup required before running (see README.md):
  - An Amazon Selling Partner (SP-API) developer application (LWA client
    id/secret) authorized against your seller account.
  - A refresh token from the authorization flow.
  - pip install python-amazon-sp-api python-dotenv
"""
import argparse
import csv
import os
import sys
import time

from sp_api.api import ListingsRestrictions
from sp_api.base import Marketplaces

from sp_api_common import build_credentials, check_asin_restriction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", help="CSV file with an 'asin' column")
    parser.add_argument("-o", "--output", default="restriction_results.csv")
    parser.add_argument(
        "-m", "--marketplace", default="US",
        help="Marketplace code understood by python-amazon-sp-api, e.g. US, CA, UK",
    )
    parser.add_argument(
        "-c", "--condition-type", default="new_new",
        help="Item condition to check restrictions for (default: new_new)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.1,
        help="Seconds to sleep between API calls to stay under rate limits",
    )
    args = parser.parse_args()

    seller_id = os.environ.get("SP_API_SELLER_ID")
    credentials = build_credentials()
    marketplace = getattr(Marketplaces, args.marketplace.upper(), Marketplaces.US)
    client = ListingsRestrictions(credentials=credentials, marketplace=marketplace)

    with open(args.input_csv, newline="") as f:
        reader = csv.DictReader(f)
        if "asin" not in (reader.fieldnames or []):
            sys.exit("Input CSV must have an 'asin' column")
        asins = [row["asin"].strip() for row in reader if row.get("asin", "").strip()]

    if not asins:
        sys.exit("No ASINs found in input CSV")

    results = []
    for i, asin in enumerate(asins, 1):
        print(f"[{i}/{len(asins)}] checking {asin}...", file=sys.stderr)
        results.append(check_asin_restriction(client, asin, seller_id, args.condition_type))
        if i < len(asins):
            time.sleep(args.delay)

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "restricted", "reasons", "error"])
        writer.writeheader()
        writer.writerows(results)

    gated = sum(1 for r in results if r["restricted"] is True)
    ungated = sum(1 for r in results if r["restricted"] is False)
    errored = sum(1 for r in results if r["restricted"] == "unknown")
    print(
        f"\nDone. {ungated} ungated, {gated} gated/restricted, {errored} errors. "
        f"Results written to {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
