# Amazon Ungated Sourcing Checklist

A workflow for vetting whether a product can be listed on Amazon without
going through brand/category approval, built around **SellerAmp SAS** as
the primary restriction-check tool. Category gating changes without
notice, so treat this as a per-product check, not a one-time category
lookup.

## 1. Category-level screening

Start with categories that are *usually* open to all professional sellers.
Even here, individual brands/ASINs inside the category can still be gated.

- Books, magazines, calendars
- Kindle / digital media (ebooks, audio)
- Beauty (most cosmetics, skincare, accessories)
- Grocery & Gourmet Food (most non-perishables)
- Home & Kitchen
- Office Products
- Sports & Outdoors
- Pet Supplies
- Clothing, Shoes & Jewelry (luxury brands often gated)
- Baby Products (some subcategories gated)
- Toys & Games (commonly re-gated during Q4 holiday season)

Categories that are almost always gated and require approval/invoices:
Automotive parts (some), Grocery (alcohol), Jewelry (fine), Watches, Media
sellers requiring pre-approval, Sexual Wellness, Streaming Media Players,
and anything DOT/FDA/hazmat regulated.

## 2. Per-product verification (do this for every ASIN before sourcing)

### Primary: SellerAmp SAS

1. **Log into Seller Central first**, in the same browser where the
   SellerAmp extension is installed — restriction status is account-
   specific, so SAS needs that session to check eligibility against *your*
   account, not a generic "is this category open" answer.
2. Browse the product on Amazon, or paste the ASIN/UPC into SellerAmp's
   lookup — the SAS data box overlays on the page.
3. Read the **restriction/eligibility indicator** in the SAS box:
   - Green / "Eligible to sell" → you can list now, no approval needed.
   - Lock icon / "Restricted" or "Approval required" → click through for
     the specific requirement (invoices, brand approval, application).
4. For a list of candidate ASINs at once, use SellerAmp's **bulk
   list/ASIN checker** instead of checking one at a time (upload a
   spreadsheet or Keepa export). Note your plan's scan-limit if you're
   batching a large catalog.
5. Sanity-check SellerAmp's profitability numbers (fees, ROI) alongside
   the restriction flag — an ungated product that doesn't clear a
   reasonable margin isn't worth sourcing anyway.

### Fallback / cross-check: Seller Central directly

Useful if SellerAmp is unavailable, rate-limited, or you want a second
source of truth before a large purchase order:

1. In Seller Central, go to **Catalog > Add Products** and search the exact
   product name, UPC/EAN, or existing ASIN.
2. Look at the listing row:
   - No badge / "Listing limits apply" → generally open.
   - **"Approval needed"** → category or brand gate; click it to see the
     requirement (invoices, letter of authorization, application form).
   - **"Restricted"** → hazmat, meltable, or otherwise blocked regardless of
     approval.
3. If sourcing from a wholesaler/distributor, confirm they can provide
   **invoices dated within the last ~180 days, quantity ≥ 10 units, with
   your business name/address** — this is the standard doc set Amazon asks
   for during ungating applications.
4. Check the brand name against Amazon's Brand Registry — registered brands
   are more likely to have proactive gating and IP complaints against
   unauthorized resellers.
5. Cross-check the ASIN's review history for authenticity complaints
   ("item not as described", counterfeit claims) — these increase suspension
   risk even on an ungated listing.

### Automated fallback: `check_listing_restrictions.py`

For bulk automation beyond SellerAmp's scan limits (e.g. checking
restriction status on a schedule, or against a large catalog you already
manage in a spreadsheet/database), the SP-API script in this folder does
the same eligibility check programmatically. See `README.md` for setup —
it needs your own SP-API developer credentials, separate from SellerAmp.

## 3. Category-specific extra requirements

- **Grocery / Health & Personal Care**: FDA facility registration or
  Certificate of Analysis may be requested for supplements.
- **Beauty**: some subcategories (e.g. professional-use) require a
  cosmetology license upload.
- **Toys**: CPSIA/ASTM safety certificates for anything marketed to
  children under 12.
- **Clothing**: no approval for most brands, but counterfeit-prone
  streetwear/luxury brands are frequently gated or IP-claimed.

## 4. Red flags — don't source without additional diligence

- Brand name is a well-known trademark and you don't have an
  invoice/authorization letter.
- Product requires batteries, is a consumable, or is otherwise flagged
  "meltable"/hazmat in Seller Central (adds FBA restrictions even if the
  listing itself is ungated).
- Category has had recent gating-policy news (check Seller Central
  announcements before large sourcing runs).

## 5. Re-verify before each reorder

Gating status is not permanent. Re-run step 2 before every reorder,
especially for beauty, grocery, and toy SKUs, since Amazon re-gates
categories seasonally (notably Toys & Games each Q4).
