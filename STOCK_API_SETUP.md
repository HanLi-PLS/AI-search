# Stock Data API Setup Guide

This document explains how to configure stock data sources for the HKEX biotech stock tracker.

## Data Source Priority

The system tries multiple data sources in order until it finds real data:

1. **Yahoo Finance (yfinance)** - Free, no API key needed
2. **Finnhub** - Reliable HK stock data (requires API key)
3. **AKShare** - Chinese markets data (no API key needed)
4. **Web Search (GPT-4.1)** - AI-powered web search fallback (requires OpenAI key)
5. **Demo Data** - Generated fallback (always available)

## Setup Instructions

### 1. Yahoo Finance (yfinance)

**Status:** ✅ Already configured (no setup needed)

**Pros:**
- Free
- No API key required
- Good HK stock coverage

**Cons:**
- Rate limited (429 errors)
- May be blocked in some regions

### 2. Finnhub (Recommended)

**Status:** 🆕 Newly integrated

**Get API Key:**
1. Sign up at https://finnhub.io/register
2. Free tier: 60 API calls/minute
3. Copy your API key from dashboard

**Configure:**
```bash
# On EC2 or your server
export FINNHUB_API_KEY="your_finnhub_api_key_here"

# For PM2 (persistent)
# Edit ecosystem.config.js or:
npx pm2 set FINNHUB_API_KEY "your_finnhub_api_key_here"
npx pm2 restart ai-search-backend --update-env
```

**Test:**
```bash
# Test in Python
python3 -c "
import requests
api_key = 'YOUR_KEY'
url = f'https://finnhub.io/api/v1/quote?symbol=2561.HK&token={api_key}'
print(requests.get(url).json())
"
```

**Pricing:**
- Free: 60 calls/min (3,600/hour)
- Paid: $59/month for more features

### 3. AKShare

**Status:** ✅ Already configured (no setup needed)

**Pros:**
- Free
- Good for Chinese markets
- No API key required

**Cons:**
- Unreliable connection from some regions
- May have rate limits

### 4. Web Search (GPT-4.1)

**Status:** ⚠️ Requires OPENAI_API_KEY

**Configure:**
```bash
# On EC2 or your server
export OPENAI_API_KEY="your_openai_api_key_here"

# For PM2
npx pm2 set OPENAI_API_KEY "your_openai_api_key_here"
npx pm2 restart ai-search-backend --update-env
```

**Cost:**
- ~$0.001-0.005 per stock lookup
- With 5-minute caching, minimal cost
- Only used when all APIs fail

## Environment Variables Summary

```bash
# Required for AI document search (already set)
OPENAI_API_KEY="sk-..."

# Optional but recommended for reliable HK stock data
FINNHUB_API_KEY="your_finnhub_key"
```

## Testing After Setup

### Check what's available:
```bash
# On your EC2 server
cd /opt/ai-search
python3 << 'EOF'
import os
from backend.app.api.routes.stocks import (
    YFINANCE_AVAILABLE,
    FINNHUB_AVAILABLE,
    AKSHARE_AVAILABLE
)

print(f"yfinance: {'✓' if YFINANCE_AVAILABLE else '✗'}")
print(f"Finnhub: {'✓' if FINNHUB_AVAILABLE else '✗'}")
print(f"AKShare: {'✓' if AKSHARE_AVAILABLE else '✗'}")
print(f"OpenAI: {'✓' if os.getenv('OPENAI_API_KEY') else '✗'}")
EOF
```

### Test stock fetching:
```bash
# Test via API
curl http://localhost:8000/api/stocks/price/2561.HK | jq '.data_source'
# Should show: "Yahoo Finance (yfinance)" or "Finnhub" or "AKShare (East Money)"
```

### Watch logs:
```bash
npx pm2 logs ai-search-backend --lines 100 | grep -E "(Trying|Got real data|failed)"
```

## Expected Log Output

**With Finnhub configured:**
```
Trying yfinance for 2561.HK
✓ Got real data from yfinance for 2561.HK
```

**When yfinance rate-limited but Finnhub works:**
```
Trying yfinance for 2561.HK
Trying Finnhub for 2561.HK
✓ Got real data from Finnhub for 2561.HK
```

**All real sources failing:**
```
Trying yfinance for 2561.HK
Trying Finnhub for 2561.HK
Trying AKShare for 2561.HK (02561)
Trying web search for 2561.HK
✓ Got real data from web search for 2561.HK: HKD XX.XX
```

## Troubleshooting

### Issue: "429 Too Many Requests" from yfinance
**Solution:** Finnhub will automatically take over. No action needed.

### Issue: "OPENAI_API_KEY not set" in logs
**Solution:**
```bash
export OPENAI_API_KEY="your-key"
npx pm2 restart ai-search-backend --update-env
```

### Issue: "No data found for X.HK in Finnhub"
**Solution:** Check if the ticker exists on HKEX and is supported by Finnhub. Some new listings may not be available yet.

### Issue: All sources showing "Demo Data"
**Solution:**
1. Check internet connectivity from EC2
2. Verify API keys are set: `env | grep -E "(FINNHUB|OPENAI)"`
3. Check PM2 environment: `npx pm2 show ai-search-backend | grep env`

## Cost Comparison

| Source | Cost | Rate Limit | HK Coverage |
|--------|------|------------|-------------|
| yfinance | Free | ~2,000/hour | Good |
| Finnhub | Free/$59/mo | 60/min | Excellent |
| AKShare | Free | Unknown | Good |
| GPT-4.1 | ~$0.005/call | High | Excellent |

## Recommendation

**Optimal Setup:**
1. ✅ yfinance (already installed) - Primary, fast
2. ✅ **Finnhub** (add API key) - Reliable fallback
3. ✅ AKShare (already installed) - Secondary fallback
4. ✅ GPT-4.1 (set OPENAI_API_KEY) - Ultimate fallback
5. ✅ Demo data - Emergency only

With this setup, you'll get real stock data 99.9% of the time!
