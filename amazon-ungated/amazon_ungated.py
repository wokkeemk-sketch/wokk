#!/usr/bin/env python3
"""
All-in-one Amazon ungated product finder.

Two modes:
  1. Discovery:  python amazon_ungated.py "silicone spatula set" -n 50
     Searches Amazon's catalog by keyword, checks each result's listing
     restriction status for your account, and writes only the ungated
     ones to a CSV.
  2. Verify:     python amazon_ungated.py --asins asins.csv
     Skips the search step and just checks restriction status for a CSV
     of ASINs you already have (needs a header row with an "asin" column).

--- SETUP ---

1. Install dependencies:
     pip install python-amazon-sp-api python-dotenv

2. Get 4 credentials from Seller Central (one-time):
     - Settings > User Permissions > enable "Amazon Selling Partner API
       Developer"
     - Partner Network > "Develop apps for Amazon" > create an app to get
       an LWA Client ID + Client Secret
     - Self-authorize the app against your own seller account to get a
       refresh token
     - Settings > Account Info for your Seller ID
   Full guide: https://developer-docs.amazon.com/sp-api/docs/registering-your-application

3. Set these as environment variables (or put them in a ".env" file in
   the same folder as this script):
     SP_API_REFRESH_TOKEN=...
     SP_API_LWA_APP_ID=...
     SP_API_LWA_CLIENT_SECRET=...
     SP_API_SELLER_ID=...

4. Run it, e.g.:
     python amazon_ungated.py "yoga mat" -n 30 -m US -o results.csv
"""
import argparse
import csv
import os
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sp_api.api import CatalogItems, ListingsRestrictions
from sp_api.base import Marketplaces, SellingApiException

REQUIRED_ENV_VARS = [
    "SP_API_REFRESH_TOKEN",
    "SP_API_LWA_APP_ID",
    "SP_API_LWA_CLIENT_SECRET",
    "SP_API_SELLER_ID",
]


def build_credentials() -> dict:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        sys.exit(
            "Missing required environment variables: " + ", ".join(missing)
            + "\nSet them in your shell, or create a .env file in this folder "
            "with SP_API_REFRESH_TOKEN, SP_API_LWA_APP_ID, "
            "SP_API_LWA_CLIENT_SECRET, SP_API_SELLER_ID."
        )
    return {
        "refresh_token": os.environ["SP_API_REFRESH_TOKEN"],
        "lwa_app_id": os.environ["SP_API_LWA_APP_ID"],
        "lwa_client_secret": os.environ["SP_API_LWA_CLIENT_SECRET"],
    }


def check_asin_restriction(client: ListingsRestrictions, asin: str, seller_id: str,
                            condition_type: str) -> dict:
    try:
        response = client.get_listings_restrictions(
            asin=asin,
            sellerId=seller_id,
            conditionType=condition_type,
        )
        restrictions = response.payload.get("restrictions", [])
        if not restrictions:
            return {"asin": asin, "restricted": False, "reasons": "", "error": ""}

        reason_texts = []
        for r in restrictions:
            for reason in r.get("reasons", []):
                reason_texts.append(reason.get("message", reason.get("reasonCode", "")))
        return {
            "asin": asin,
            "restricted": True,
            "reasons": " | ".join(reason_texts),
            "error": "",
        }
    except SellingApiException as e:
        return {"asin": asin, "restricted": "unknown", "reasons": "", "error": str(e)}


def search_catalog(client: CatalogItems, keywords: str, max_results: int,
                    marketplace_id: str) -> list:
    candidates = []
    seen = set()
    page_token = None

    while len(candidates) < max_results:
        kwargs = {
            "keywords": [keywords],
            "marketplaceIds": [marketplace_id],
            "includedData": ["summaries"],
            "pageSize": min(20, max_results - len(candidates)),
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
            candidates.append({
                "asin": asin,
                "title": summary.get("itemName", ""),
                "brand": summary.get("brandName", ""),
            })

        page_token = response.payload.get("pagination", {}).get("nextToken")
        if not page_token:
            break

    return candidates[:max_results]


def load_asins_csv(path: str) -> list:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if "asin" not in (reader.fieldnames or []):
            sys.exit("Input CSV must have an 'asin' column")
        return [
            {"asin": row["asin"].strip(), "title": "", "brand": ""}
            for row in reader if row.get("asin", "").strip()
        ]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="?", help="Search term, e.g. 'silicone spatula set'")
    parser.add_argument("--asins", help="CSV file with an 'asin' column to check instead of searching")
    parser.add_argument("-o", "--output", default="ungated_results.csv")
    parser.add_argument("-n", "--max-results", type=int, default=50,
                         help="Max candidates to pull from catalog search (default: 50)")
    parser.add_argument("-m", "--marketplace", default="US",
                         help="Marketplace code, e.g. US, CA, UK (default: US)")
    parser.add_argument("-c", "--condition-type", default="new_new",
                         help="Item condition to check restrictions for (default: new_new)")
    parser.add_argument("--delay", type=float, default=1.1,
                         help="Seconds between restriction-check calls (default: 1.1)")
    parser.add_argument("--keep-gated", action="store_true",
                         help="Write every candidate with its status, instead of only ungated ones")
    args = parser.parse_args()

    if not args.keywords and not args.asins:
        parser.error("provide either a search keyword or --asins <file.csv>")

    seller_id = os.environ.get("SP_API_SELLER_ID")
    credentials = build_credentials()
    marketplace = getattr(Marketplaces, args.marketplace.upper(), Marketplaces.US)
    restrictions_client = ListingsRestrictions(credentials=credentials, marketplace=marketplace)

    if args.asins:
        candidates = load_asins_csv(args.asins)
        print(f"Loaded {len(candidates)} ASINs from {args.asins}. Checking restrictions...", file=sys.stderr)
    else:
        catalog_client = CatalogItems(credentials=credentials, marketplace=marketplace)
        print(f"Searching catalog for '{args.keywords}'...", file=sys.stderr)
        candidates = search_catalog(catalog_client, args.keywords, args.max_results, marketplace.marketplace_id)
        if not candidates:
            sys.exit("No catalog results found for that search term.")
        print(f"Found {len(candidates)} candidate products. Checking restrictions...", file=sys.stderr)

    results = []
    for i, candidate in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] checking {candidate['asin']}...", file=sys.stderr)
        restriction = check_asin_restriction(restrictions_client, candidate["asin"], seller_id, args.condition_type)
        results.append({**candidate, **restriction})
        if i < len(candidates):
            time.sleep(args.delay)

    ungated = [r for r in results if r["restricted"] is False]
    output_rows = results if args.keep_gated else ungated

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "title", "brand", "restricted", "reasons", "error"])
        writer.writeheader()
        writer.writerows(output_rows)

    gated = sum(1 for r in results if r["restricted"] is True)
    errored = sum(1 for r in results if r["restricted"] == "unknown")
    print(
        f"\nDone. {len(ungated)} ungated / {len(candidates)} checked "
        f"({gated} gated, {errored} errors). Results written to {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
