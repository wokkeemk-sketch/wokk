#!/usr/bin/env python3
"""
Score and filter Amazon FBA product leads from SellerAmp SAS and/or Keepa
CSV exports — no Amazon SP-API developer account needed.

Usage:
  python analyze_leads.py --sellerapp sas_export.csv --keepa keepa_export.csv -o leads.csv
  python analyze_leads.py --sellerapp sas_export.csv          # SellerAmp only
  python analyze_leads.py --keepa keepa_export.csv            # Keepa only

How to get the input files:
  - SellerAmp SAS: run a bulk ASIN/list scan (Tools > Bulk Search, or upload
    a CSV of ASINs), then export the results to CSV. This is what supplies
    the restriction/eligibility status and live profit/ROI numbers.
  - Keepa: use Product Finder to build a filtered list (category, BSR range,
    price range, etc.), then export to CSV. This supplies rank, price
    history, and competition data over time.

You can pass one or both files. Columns are matched by common header
names/aliases used by each tool's export, so exact formatting doesn't
need to match — but if a column you expect isn't showing up in the
output, open the CSV and check the header text against ALIASES below.

The script:
  1. Loads whichever files you pass and normalizes their columns.
  2. Merges rows by ASIN if both files are given.
  3. Excludes gated/restricted ASINs by default (see --include-gated).
  4. Applies beginner-friendly threshold filters (see --help for all of
     them) — tune these to your niche/budget.
  5. Scores surviving rows 0-100 on ROI, profit, rank, competition,
     rating, and reviews (using whatever fields are actually present)
     and writes the sorted result to CSV.
"""
import argparse
import csv
import re
import sys

ALIASES = {
    "asin": ["asin"],
    "title": ["title", "product name", "item name", "productname"],
    "brand": ["brand", "brand name"],
    "category": ["category", "categories", "root category", "product category"],
    "eligibility": [
        "restrictions", "restriction", "restricted", "eligibility",
        "eligible to sell", "gated", "sell status", "listing restrictions",
        "can i sell", "ineligibility reasons",
    ],
    "price": ["sale price", "buy box price", "buy box current", "price",
              "current price", "buybox price"],
    "fba_fees": ["fba fees", "fba fee", "amazon fees", "fulfillment fee"],
    "profit": ["profit", "net profit", "estimated profit"],
    "roi": ["roi", "roi percent", "return on investment"],
    "rank": ["sales rank", "bsr", "sales rank current", "current sales rank", "rank"],
    "monthly_sales": ["est monthly sales", "estimated monthly sales",
                       "monthly sales", "sales mo", "est sales"],
    "sellers": ["number of sellers", "offer count", "fba sellers",
                "total offers", "seller count", "competing sellers",
                "of sellers"],
    "rating": ["rating", "review rating", "star rating"],
    "reviews": ["reviews", "review count", "number of reviews", "rating count"],
}

GATED_PHRASES = [
    "not eligible", "ineligible", "approval required", "approval needed",
    "requires approval", "requires invoice", "restricted", "gated", "blocked",
]
UNGATED_PHRASES = [
    "eligible to sell", "eligible", "ungated", "clear to sell",
    "ready to sell", "not restricted", "no restriction",
]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def build_column_map(headers: list) -> dict:
    normed = {h: norm(h) for h in headers}
    column_map = {}
    for canonical, aliases in ALIASES.items():
        for header, nh in normed.items():
            if nh in aliases or any(a in nh for a in aliases):
                column_map[canonical] = header
                break
    return column_map


def parse_number(s):
    if s is None:
        return None
    s = s.strip()
    if not s or s.lower() in ("n/a", "na", "-", "unknown"):
        return None
    s = s.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_eligibility(raw):
    if raw is None:
        return None
    v = raw.strip().lower()
    if not v:
        return None
    if any(p in v for p in GATED_PHRASES):
        return True
    if any(p in v for p in UNGATED_PHRASES):
        return False
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


def load_csv(path: str, source_label: str) -> dict:
    """Returns {asin: row_dict} with normalized canonical fields."""
    rows = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        column_map = build_column_map(headers)
        if "asin" not in column_map:
            sys.exit(f"{path}: couldn't find an ASIN column among: {headers}")

        for raw_row in reader:
            asin = (raw_row.get(column_map["asin"]) or "").strip().upper()
            if not asin:
                continue
            entry = {"asin": asin, "sources": {source_label}}
            for field in ("title", "brand", "category"):
                col = column_map.get(field)
                entry[field] = (raw_row.get(col) or "").strip() if col else ""
            for field in ("price", "fba_fees", "profit", "roi", "rank",
                          "monthly_sales", "sellers", "rating", "reviews"):
                col = column_map.get(field)
                entry[field] = parse_number(raw_row.get(col)) if col else None
            col = column_map.get("eligibility")
            entry["gated"] = parse_eligibility(raw_row.get(col)) if col else None
            rows[asin] = entry
    return rows


def merge_rows(sellerapp_rows: dict, keepa_rows: dict) -> list:
    all_asins = set(sellerapp_rows) | set(keepa_rows)
    merged = []
    for asin in all_asins:
        sa = sellerapp_rows.get(asin)
        kp = keepa_rows.get(asin)
        row = {"asin": asin, "sources": set()}
        if sa:
            row["sources"] |= sa["sources"]
        if kp:
            row["sources"] |= kp["sources"]

        row["title"] = (sa and sa["title"]) or (kp and kp["title"]) or ""
        row["brand"] = (sa and sa["brand"]) or (kp and kp["brand"]) or ""
        row["category"] = (sa and sa["category"]) or (kp and kp["category"]) or ""
        row["gated"] = (sa and sa["gated"]) if sa and sa["gated"] is not None else (kp and kp["gated"])

        # SellerAmp is authoritative for live pricing/profit/ROI (it checks
        # against your account's current fee schedule); Keepa is authoritative
        # for rank/competition/reviews (it tracks these over time).
        row["price"] = (sa and sa["price"]) if sa and sa["price"] is not None else (kp and kp["price"])
        row["fba_fees"] = (sa and sa["fba_fees"]) if sa else None
        row["profit"] = (sa and sa["profit"]) if sa else None
        row["roi"] = (sa and sa["roi"]) if sa else None
        row["rank"] = (kp and kp["rank"]) if kp and kp["rank"] is not None else (sa and sa["rank"])
        row["monthly_sales"] = (kp and kp["monthly_sales"]) if kp else (sa and sa["monthly_sales"])
        row["sellers"] = (kp and kp["sellers"]) if kp else (sa and sa["sellers"])
        row["rating"] = (kp and kp["rating"]) if kp and kp["rating"] is not None else (sa and sa["rating"])
        row["reviews"] = (kp and kp["reviews"]) if kp and kp["reviews"] is not None else (sa and sa["reviews"])
        merged.append(row)
    return merged


def score_row(row) -> float:
    parts = []  # (points, max_points)

    if row["roi"] is not None:
        parts.append((min(30, max(0, row["roi"] / 100 * 30)), 30))
    if row["profit"] is not None:
        parts.append((min(20, max(0, row["profit"] / 10 * 20)), 20))
    if row["rank"] is not None:
        r = row["rank"]
        pts = 20 if r <= 10000 else 15 if r <= 50000 else 10 if r <= 150000 else 5 if r <= 300000 else 0
        parts.append((pts, 20))
    if row["sellers"] is not None:
        s = row["sellers"]
        pts = 15 if s <= 3 else 10 if s <= 8 else 5 if s <= 15 else 0
        parts.append((pts, 15))
    if row["rating"] is not None:
        parts.append((min(10, max(0, row["rating"] / 5 * 10)), 10))
    if row["reviews"] is not None:
        rv = row["reviews"]
        pts = 5 if rv >= 50 else 3 if rv >= 10 else 0
        parts.append((pts, 5))

    if not parts:
        return None
    total_pts = sum(p for p, _ in parts)
    total_max = sum(m for _, m in parts)
    return round(total_pts / total_max * 100, 1)


def passes_filters(row, args) -> bool:
    if row["gated"] is True and not args.include_gated:
        return False
    if row["roi"] is not None and row["roi"] < args.min_roi:
        return False
    if row["profit"] is not None and row["profit"] < args.min_profit:
        return False
    if row["rank"] is not None and row["rank"] > args.max_rank:
        return False
    if row["monthly_sales"] is not None and row["monthly_sales"] < args.min_monthly_sales:
        return False
    if row["sellers"] is not None and row["sellers"] > args.max_sellers:
        return False
    if row["price"] is not None and not (args.min_price <= row["price"] <= args.max_price):
        return False
    if row["rating"] is not None and row["rating"] < args.min_rating:
        return False
    if row["reviews"] is not None and row["reviews"] < args.min_reviews:
        return False
    return True


def gated_label(g):
    if g is True:
        return "gated"
    if g is False:
        return "ungated"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sellerapp", help="SellerAmp SAS bulk-scan CSV export")
    parser.add_argument("--keepa", help="Keepa Product Finder CSV export")
    parser.add_argument("-o", "--output", default="scored_leads.csv")
    parser.add_argument("--top", type=int, default=20, help="Print top N to console (default: 20)")
    parser.add_argument("--include-gated", action="store_true",
                         help="Keep gated/restricted ASINs in the output instead of dropping them")
    parser.add_argument("--min-roi", type=float, default=30.0, help="Minimum ROI %% (default: 30)")
    parser.add_argument("--min-profit", type=float, default=3.0, help="Minimum profit per unit, $ (default: 3)")
    parser.add_argument("--max-rank", type=float, default=150000, help="Maximum sales rank/BSR (default: 150000)")
    parser.add_argument("--min-monthly-sales", type=float, default=10,
                         help="Minimum estimated monthly sales (default: 10)")
    parser.add_argument("--max-sellers", type=float, default=15,
                         help="Maximum competing sellers/offers (default: 15)")
    parser.add_argument("--min-price", type=float, default=10, help="Minimum sale price, $ (default: 10)")
    parser.add_argument("--max-price", type=float, default=50, help="Maximum sale price, $ (default: 50)")
    parser.add_argument("--min-rating", type=float, default=3.8, help="Minimum star rating (default: 3.8)")
    parser.add_argument("--min-reviews", type=float, default=0, help="Minimum review count (default: 0)")
    args = parser.parse_args()

    if not args.sellerapp and not args.keepa:
        parser.error("provide --sellerapp <file.csv>, --keepa <file.csv>, or both")

    sellerapp_rows = load_csv(args.sellerapp, "sellerapp") if args.sellerapp else {}
    keepa_rows = load_csv(args.keepa, "keepa") if args.keepa else {}
    merged = merge_rows(sellerapp_rows, keepa_rows)

    print(f"Loaded {len(merged)} unique ASINs.", file=sys.stderr)

    scored = []
    for row in merged:
        row["score"] = score_row(row)
        scored.append(row)

    kept = [r for r in scored if passes_filters(r, args)]
    kept.sort(key=lambda r: (r["score"] is not None, r["score"]), reverse=True)

    fieldnames = ["asin", "title", "brand", "category", "gated", "price",
                  "fba_fees", "profit", "roi", "rank", "monthly_sales",
                  "sellers", "rating", "reviews", "score", "sources"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in kept:
            out = {k: r.get(k) for k in fieldnames}
            out["gated"] = gated_label(r["gated"])
            out["sources"] = "+".join(sorted(r["sources"]))
            writer.writerow(out)

    gated_count = sum(1 for r in scored if r["gated"] is True)
    print(
        f"{len(kept)} passed filters / {len(scored)} total "
        f"({gated_count} gated excluded). Written to {args.output}",
        file=sys.stderr,
    )

    if args.top and kept:
        def fmt(v):
            if v is None:
                return "-"
            return str(int(v)) if float(v).is_integer() else f"{v:.1f}"

        print(f"\nTop {min(args.top, len(kept))} leads:\n", file=sys.stderr)
        header = f"{'ASIN':<12} {'Score':>6} {'ROI%':>7} {'Profit':>8} {'Rank':>9} {'Sellers':>8}  Title"
        print(header, file=sys.stderr)
        for r in kept[: args.top]:
            print(
                f"{r['asin']:<12} "
                f"{fmt(r['score']):>6} "
                f"{fmt(r['roi']):>7} "
                f"{fmt(r['profit']):>8} "
                f"{fmt(r['rank']):>9} "
                f"{fmt(r['sellers']):>8}  "
                f"{r['title'][:60]}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
