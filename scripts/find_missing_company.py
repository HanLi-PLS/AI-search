#!/usr/bin/env python3
"""
Find which company is missing from the scraped data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import FALLBACK_HKEX_BIOTECH_COMPANIES, scrape_hkex_biotech_companies

print("="*70)
print("COMPARING SCRAPED VS FALLBACK COMPANY LIST")
print("="*70)

fallback_codes = {c['code']: c for c in FALLBACK_HKEX_BIOTECH_COMPANIES}
print(f"\nFallback list: {len(fallback_codes)} companies")

scraped = scrape_hkex_biotech_companies()

if scraped:
    scraped_codes = {c['code']: c for c in scraped}
    print(f"Scraped list: {len(scraped_codes)} companies")

    # Find missing companies
    missing_codes = set(fallback_codes.keys()) - set(scraped_codes.keys())

    if missing_codes:
        print(f"\n⚠ MISSING COMPANIES ({len(missing_codes)}):")
        for code in sorted(missing_codes):
            company = fallback_codes[code]
            print(f"  {code} - {company['ticker']} - {company['name']}")
    else:
        print("\n✓ All companies found!")

    # Find extra companies (shouldn't happen)
    extra_codes = set(scraped_codes.keys()) - set(fallback_codes.keys())

    if extra_codes:
        print(f"\n⚠ EXTRA COMPANIES ({len(extra_codes)}):")
        for code in sorted(extra_codes):
            company = scraped_codes[code]
            print(f"  {code} - {company['ticker']} - {company['name']}")

    # Check if names match (might have encoding issues)
    print("\n" + "="*70)
    print("CHECKING FOR NAME MISMATCHES")
    print("="*70)

    for code in sorted(scraped_codes.keys()):
        if code in fallback_codes:
            scraped_name = scraped_codes[code]['name']
            fallback_name = fallback_codes[code]['name']
            if scraped_name != fallback_name:
                print(f"\n{code}:")
                print(f"  Scraped:  {scraped_name}")
                print(f"  Fallback: {fallback_name}")
else:
    print("\n✗ Scraping failed completely")
