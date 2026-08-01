# Amazon Ungated Product Tools

Tools for figuring out what you can list on Amazon without going through
category/brand approval:

1. **[CHECKLIST.md](./CHECKLIST.md)** — a manual, no-setup workflow to vet
   products in Seller Central (or via SellerAmp) before sourcing.
2. **`find_ungated_products.py`** — searches Amazon's catalog by keyword
   and returns only the results that are ungated for your account. Use
   this to *discover* candidate products.
3. **`check_listing_restrictions.py`** — checks restriction status for a
   batch of ASINs you already have. Use this to *verify* a list you've
   already sourced (e.g. from a supplier catalog).

Both scripts call Amazon's SP-API and need the same credentials — set up
once, use either script.

## Setup (shared by both scripts)

### 1. Get SP-API credentials

You need a Selling Partner API developer application authorized against
your seller account:

1. Register as a developer in Seller Central: **Settings > User
   Permissions > Amazon Selling Partner API Developer**.
2. Create an app in **Partner Network > Develop apps for Amazon** (LWA
   client ID + client secret).
3. Authorize the app against your seller account to get a **refresh
   token** (self-authorization flow if it's your own store, or the OAuth
   flow if this app will be used by other sellers).
4. Find your **Seller ID** under Settings > Account Info.

Full walkthrough: https://developer-docs.amazon.com/sp-api/docs/registering-your-application

Note: the Listings Restrictions endpoint this script uses does not require
AWS IAM/SigV4 signing (SP-API moved to LWA-only auth), so you only need the
four values above — no AWS access key needed.

### 2. Install dependencies

```bash
cd amazon-ungated
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# then edit .env and fill in SP_API_REFRESH_TOKEN, SP_API_LWA_APP_ID,
# SP_API_LWA_CLIENT_SECRET, SP_API_SELLER_ID
```

## Option A: Discover ungated products by keyword

```bash
python find_ungated_products.py "silicone spatula set" -o results.csv -n 50 -m US
```

This searches the Amazon catalog for up to `-n` candidates matching your
keywords, checks each one's restriction status, and writes only the
ungated ones to `results.csv` (pass `--keep-gated` to write every
candidate with its status instead of filtering).

Output CSV columns: `asin`, `title`, `brand`, `restricted`, `reasons`, `error`
(same meaning as below).

## Option B: Verify a list of ASINs you already have

Copy `asins.example.csv` to `asins.csv` and replace with the ASINs you're
evaluating (one per row, header must include `asin`), then:

```bash
python check_listing_restrictions.py asins.csv -o results.csv -m US
```

Output CSV columns:

| column | meaning |
|---|---|
| `asin` | the ASIN checked |
| `restricted` | `False` = ungated for your account, `True` = approval/authorization required, `unknown` = API error (see `error` column) |
| `reasons` | Amazon's stated reason(s) when restricted, e.g. "You need approval to sell this product" |
| `error` | raw API error message, if the call failed |

### Rate limits

Both the Catalog Items search and Listings Restrictions endpoints are
rate-limited (a few requests/sec, refilling slower). Each script sleeps
`--delay` seconds (default 1.1s) between restriction-check calls; increase
it if you see throttling errors. `find_ungated_products.py` checks
restrictions for every candidate found, so a large `-n` will take
proportionally longer.

## Notes

- Restriction status is specific to *your* seller account — a category open
  to one seller can still be gated for another based on account history,
  performance metrics, or existing approvals.
- Re-run checks periodically; gating changes without notice (see
  CHECKLIST.md section 5).
- `.env` and any `asins.csv`/`results.csv` you create are gitignored — never
  commit real credentials or sourcing lists.
