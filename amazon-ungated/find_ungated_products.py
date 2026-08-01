#!/usr/bin/env python3
"""
Find Amazon products matching a search term that are ungated for your
seller account.

Two-step pipeline:
  1. Search Amazon's catalog via SP-API Catalog Items for candidate ASINs
     matching your keywords.
  2. Check each candidate's listing restriction status via the SP-API
     Listings Restrictions endpoint, keeping only the ungated ones.

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

from sp_api.api import CatalogItems, ListingsRestrictions
from sp_api.base import Marketplaces, SellingApiException

from sp_api_common import build_credentials, check_asin_restriction


def search_catalog(client: CatalogItems, keywords: str, max_results: int,
                    marketplace_id: str) -> list:
    asins = []
    seen = set()
    page_token = None

    while len(asins) < max_results:
        kwargs = {
            "keywords": [keywords],
            "marketplaceIds": [marketplace_id],
            "includedData": ["summaries"],
            "pageSize": min(20, max_results - len(asins)),
        }
        if page_token:
            kwargs["pageToken"] = page_token

        try:
            response = client.search_catalog_items(**kwargs)
        except SellingApiException as e:
            print(f"Catalog search failed: {e}", file=sys.stderr)
            break

        items = response.payload.get("items", [])
        if not items:
            break

        for item in items:
            asin = item.get("asin")
            if not asin or asin in seen:
                continue
            seen.add(asin)
            summary = (item.get("summaries") or [{}])[0]
            asins.append({
                "asin": asin,
                "title": summary.get("itemName", ""),
                "brand": summary.get("brandName", ""),
            })

        page_token = response.payload.get("pagination", {}).get("nextToken")
        if not page_token:
            break

    return asins[:max_results]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keywords", help="Search term, e.g. 'silicone spatula set'")
    parser.add_argument("-o", "--output", default="ungated_products.csv")
    parser.add_argument(
        "-n", "--max-results", type=int, default=50,
        help="Max candidate products to pull from the catalog search (default: 50)",
    )
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
        help="Seconds to sleep between restriction-check calls to stay under rate limits",
    )
    parser.add_argument(
        "--keep-gated", action="store_true",
        help="Write all candidates to output with their status, instead of only ungated ones",
    )
    args = parser.parse_args()

    seller_id = os.environ.get("SP_API_SELLER_ID")
    credentials = build_credentials()
    marketplace = getattr(Marketplaces, args.marketplace.upper(), Marketplaces.US)

    catalog_client = CatalogItems(credentials=credentials, marketplace=marketplace)
    restrictions_client = ListingsRestrictions(credentials=credentials, marketplace=marketplace)

    print(f"Searching catalog for '{args.keywords}'...", file=sys.stderr)
    candidates = search_catalog(
        catalog_client, args.keywords, args.max_results, marketplace.marketplace_id
    )
    if not candidates:
        sys.exit("No catalog results found for that search term.")
    print(f"Found {len(candidates)} candidate products. Checking restrictions...", file=sys.stderr)

    results = []
    for i, candidate in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] checking {candidate['asin']}...", file=sys.stderr)
        restriction = check_asin_restriction(
            restrictions_client, candidate["asin"], seller_id, args.condition_type
        )
        results.append({**candidate, **restriction})
        if i < len(candidates):
            time.sleep(args.delay)

    ungated = [r for r in results if r["restricted"] is False]
    output_rows = results if args.keep_gated else ungated

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["asin", "title", "brand", "restricted", "reasons", "error"]
        )
        writer.writeheader()
        writer.writerows(output_rows)

    gated = sum(1 for r in results if r["restricted"] is True)
    errored = sum(1 for r in results if r["restricted"] == "unknown")
    print(
        f"\nDone. {len(ungated)} ungated / {len(candidates)} candidates "
        f"({gated} gated, {errored} errors). Results written to {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
