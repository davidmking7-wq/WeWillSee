# H33 locked-data source audit

Status: **DATA_INCONCLUSIVE — no historical stage has been run.**  This is a
data verdict, not a strategy verdict.  The H33 preregistration and hash remain
unchanged.

This audit was performed after the protocol lock at commit `c9a8b39`.  The
strict runner requires every data-quality flag to be true.  None may be set to
true on the strength of a vendor's marketing claim or a current-constituent
list.

## Blocking facts

### 1. The GDELT record cannot satisfy the locked clock rule for all stages

The rule requires every document to be assigned using its publication time and
the primary exchange's official close.  GDELT GKG 1.0, the only main news GKG
available for most of 2014, stores only `YYYYMMDD` in its `DATE` field.  Its
official archive starts on 2013-04-01 and provides daily ZIPs, but a date without
a time cannot determine whether an article appeared before or after the close.
The official GKG 1.0 codebook and archive are:

- https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook.pdf
- http://data.gdeltproject.org/gkg/index.html

GDELT says the GKG 2.x stream begins on 2015-02-19.  Its 2.1 `DATE` field is a
14-digit `YYYYMMDDHHMMSS` timestamp and the archive updates every 15 minutes,
so it cannot backfill 2014 under the locked definition:

- https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
- https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf

The official manifests fetched on 2026-08-10 have no full daily GKG files from
2025-06-14 through 2025-07-01 inclusive.  The 2.x master list also has no GKG
batches for 2025-06-15 through 2025-07-01 and only 72 of the expected 96
batches on 2025-06-14.  Therefore `gdelt_archive_days_complete=true` cannot be
certified for either 2017–2025 historical stage.  Refresh the manifests and
reproduce the check with:

```powershell
python -m validation_protocol.gdelt_archive_audit audit `
  --stream v1 --start 2017-01-03 --end 2025-12-31 --refresh

python -m validation_protocol.gdelt_archive_audit audit `
  --stream v2 --start 2017-01-03 --end 2025-12-31 --refresh
```

The audit cross-checks GDELT's published byte counts and MD5 manifests.  Only
`download --execute` verifies downloaded file bytes against those values; the
plain `audit` command checks manifest inventory.  GDELT serves these endpoints
over unauthenticated HTTP, so the checks detect inconsistencies and make a run
reproducible but do not cryptographically prove that GDELT authored the bytes.
The downloader pins every file to the exact official host, does not follow HTTP
redirects, and refuses malformed or conflicting manifest entries.  File
presence still does not prove complete article capture.

### 2. No free source found covers the locked point-in-time universes

S&P states that the Composite 1500 combines the S&P 500, MidCap 400 and
SmallCap 600, and its methodology says composition changes are made as needed,
not just at a fixed annual rebuild.  The public page exposes current
constituents and public change announcements, not an audited daily history with
dead firms and permanent company identifiers:

- https://www.spglobal.com/spdji/en/indices/equity/sp-composite-1500/
- https://www.spglobal.com/spdji/en/methodology/article/sp-us-indices-methodology/

FTSE Russell publishes current FTSE 350 constituents plus official historic
addition/deletion PDFs for the FTSE 100 and FTSE 250.  Those history PDFs use
company names, not stable instrument/company IDs, and cannot by themselves
resolve renamed share lines, mergers, duplicate classes, or terminal values:

- https://www.lseg.com/en/ftse-russell/indices/uk
- https://www.lseg.com/content/dam/ftse-russell/en_us/documents/policy-documents/ftse-100-constituent-history.pdf
- https://www.lseg.com/content/dam/ftse-russell/en_us/documents/policy-documents/ftse-250-constituent-history.pdf

LSEG's commercial Indices, Constituents and Weightings dataset explicitly
offers composition/weight history and delivery through licensed products.  It
is the authoritative practical route for FTSE history, but it is not an open
download:

- https://www.lseg.com/en/data-analytics/financial-data/indices/equity-indices/indices-constituents-weightings

### 3. Free price feeds do not certify the locked open-to-open total return

The contract needs raw dollar volume plus a consistent USD open and close total
return series that carries acquisition or delisting value through the planned
exit.  A feed that merely retains a last quote, supplies adjusted close only,
or omits dead tickers fails this gate.

CRSP documents the needed US building blocks: permanent `PERMNO`/`PERMCO`,
daily opening price, distributions, and a separately researched delisting
total return.  CRSP is licensed institutional/academic data, not a free
individual feed:

- https://www.crsp.org/research/
- https://www.crsp.org/wp-content/uploads/guides/CRSP10_Year_US_Stock_Database_Guide.pdf
- https://www.crsp.org/subscription-information/

For the UK, LSEG Datastream/DataScope can supply historical LSE prices,
corporate actions, identifiers, opening price (`PO`) and return index (`RI`),
while LSEG PermID supplies permanent organization/instrument identifiers.  The
price/history products require an entitlement; basic PermID lookup is open:

- https://www.lseg.com/en/data-analytics/financial-data/pricing-and-market-data/equities-market-data/lse-market-data
- https://developers.lseg.com/en/api-catalog/open-perm-id/permid-record-matching-restful-api/documentation/overview-and-concepts/faq

## Gate-by-gate source result

| Locked field | Free attempt | Verdict | Strict practical source |
|---|---|---|---|
| Point-in-time S&P 1500, including dead firms | Current S&P pages and announcements | Not a complete permanent-ID panel | Licensed S&P constituent history/Compustat index history; reconcile to CRSP |
| Point-in-time FTSE 350, including dead firms | Current list + official FTSE 100/250 change PDFs | Names/events exist, but stable security mapping is unaudited | LSEG FTSE/ICW constituent history |
| Permanent company ID | CIK/ISIN/SEDOL/ticker/Open PermID | Open PermID is useful; ticker/ISIN/SEDOL alone are not company-lifetime IDs | CRSP `PERMCO` in US; LSEG Organization PermID in UK |
| Total-return open and close | Free adjusted-close feeds | Adjusted open and terminal proceeds cannot be certified | CRSP daily stock/distribution/delist files; LSEG `PO`/`P`/`RI` plus corporate actions/dead equities |
| Contemporaneous USD dollar volume | Free OHLCV/FX | Possible for active names, incomplete for dead histories | CRSP volume/price in US; LSEG turnover/price/currency in UK |
| Complete GDELT organization mentions | Official GKG archives | Fatal 2014 time precision issue and 2025 archive gap | No provider can recreate records GDELT did not publish; H33 V1 remains inconclusive |
| Frozen audited alias map | Company names plus public identifiers | Buildable only after universe IDs are licensed/frozen | Freeze CRSP/LSEG entity master first, hash it, then count GDELT records without looking at returns |

## Cheapest useful dry run versus a confirmatory run

Norgate Data's US Platinum tier advertises delisted securities and historical
S&P Composite 1500 membership and currently lists a 12-month price of USD 630.
It can support a useful US engineering dry run.  Its own page says the US
constituent history is “essentially complete,” so it should not independently
certify the locked authoritative membership/delisting gates without a source
audit.  It also does not provide the required UK stock universe:

- https://norgatedata.com/data-content-tables.php
- https://norgatedata.com/stockmarketpackages.php

EODHD advertises delisted tickers and index membership history, but its EOD
schema supplies raw OHLC plus adjusted close rather than an adjusted total-
return open, and the documentation does not certify final delisting proceeds.
It is suitable only for a proxy dry run:

- https://eodhd.com/financial-apis/delisted-stock-companies-data-2
- https://eodhd.com/financial-apis/api-for-historical-data-and-volumes

The strict historical H33 V1 test cannot be completed even after buying market
data because the locked GDELT requirements fail independently.  The honest next
use of the existing protocol is the future-paper stage, starting from complete
post-lock GKG 2.x files, with a frozen licensed/current point-in-time universe
and alias map.  Any historical workaround (dropping the 2025 outage, assigning
2014 articles to midnight, or changing the source) would be a new protocol and
a new trial, exactly as the lock requires.
