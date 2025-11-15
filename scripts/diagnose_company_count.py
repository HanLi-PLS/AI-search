#!/usr/bin/env python3
"""
Diagnose the company count issue
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import FALLBACK_HKEX_BIOTECH_COMPANIES, scrape_hkex_biotech_companies, get_hkex_biotech_companies

print("="*70)
print("FALLBACK COMPANY LIST ANALYSIS")
print("="*70)

print(f"\nTotal companies in FALLBACK_HKEX_BIOTECH_COMPANIES: {len(FALLBACK_HKEX_BIOTECH_COMPANIES)}")

# Check for duplicates by code
codes_seen = {}
for idx, company in enumerate(FALLBACK_HKEX_BIOTECH_COMPANIES):
    code = company['code']
    if code in codes_seen:
        print(f"⚠ DUPLICATE CODE: {code} at index {idx} and {codes_seen[code]}")
        print(f"  First: {FALLBACK_HKEX_BIOTECH_COMPANIES[codes_seen[code]]}")
        print(f"  Second: {company}")
    else:
        codes_seen[code] = idx

# Check for duplicates by ticker
tickers_seen = {}
for idx, company in enumerate(FALLBACK_HKEX_BIOTECH_COMPANIES):
    ticker = company['ticker']
    if ticker in tickers_seen:
        print(f"⚠ DUPLICATE TICKER: {ticker} at index {idx} and {tickers_seen[ticker]}")
        print(f"  First: {FALLBACK_HKEX_BIOTECH_COMPANIES[tickers_seen[ticker]]}")
        print(f"  Second: {company}")
    else:
        tickers_seen[ticker] = idx

print(f"\nUnique codes: {len(codes_seen)}")
print(f"Unique tickers: {len(tickers_seen)}")

# Test the API function
print("\n" + "="*70)
print("TESTING get_hkex_biotech_companies() FUNCTION")
print("="*70)

companies = get_hkex_biotech_companies()
print(f"\nTotal companies returned: {len(companies)}")

# Check what's returned
returned_codes = set(c['code'] for c in companies)
fallback_codes = set(c['code'] for c in FALLBACK_HKEX_BIOTECH_COMPANIES)

print(f"Unique codes returned: {len(returned_codes)}")

if returned_codes != fallback_codes:
    missing = fallback_codes - returned_codes
    extra = returned_codes - fallback_codes

    if missing:
        print(f"\n⚠ MISSING CODES ({len(missing)}):")
        for code in sorted(missing):
            company = next(c for c in FALLBACK_HKEX_BIOTECH_COMPANIES if c['code'] == code)
            print(f"  {code} - {company['ticker']} - {company['name']}")

    if extra:
        print(f"\n⚠ EXTRA CODES ({len(extra)}):")
        for code in sorted(extra):
            company = next(c for c in companies if c['code'] == code)
            print(f"  {code} - {company['ticker']} - {company['name']}")

# List all companies
print("\n" + "="*70)
print("ALL COMPANIES IN FALLBACK LIST:")
print("="*70)
for idx, company in enumerate(FALLBACK_HKEX_BIOTECH_COMPANIES, 1):
    print(f"{idx:2d}. {company['code']} | {company['ticker']:10s} | {company['name']}")

print("\n" + "="*70)
print(f"TOTAL: {len(FALLBACK_HKEX_BIOTECH_COMPANIES)} companies")
print("="*70)
