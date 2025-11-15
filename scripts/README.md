# Utility Scripts

## update_biotech_companies.py

Tests whether AAStocks web scraping and AKShare data fetching work from your network location.

### Usage

On your EC2 instance:

```bash
cd /opt/ai-search  # or wherever your app is deployed
python3 scripts/update_biotech_companies.py
```

### What it does

1. **Tests AAStocks scraping** - Tries to fetch the biotech company list from AAStocks
2. **Tests AKShare** - Tries to fetch HK stock data and filter for biotech companies
3. **Outputs results** - Shows which methods work and generates updated company list

### If scraping works

The script will output Python code you can use to update the `FALLBACK_HKEX_BIOTECH_COMPANIES` list in `backend/app/api/routes/stocks.py` with the latest data.

### If scraping fails

The application will continue using the hardcoded fallback list (19 companies), which ensures the stock tracker keeps working even when scraping is blocked.

### Why run on EC2?

Web scraping often works differently depending on:
- Network location / IP address
- Geo-blocking policies
- Rate limiting per IP

This script is blocked in some development environments but may work fine from your EC2 instance's network.
