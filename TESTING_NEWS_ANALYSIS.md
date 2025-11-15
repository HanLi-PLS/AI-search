# 🧪 Testing AI News Analysis Feature

## Why You Don't See It

The AI news analysis feature **IS working**, but it only appears when stocks have **≥10% price moves**. On a typical trading day, most stocks don't move this much, so you won't see the feature.

### Feature Activation Criteria

The feature triggers when EITHER:
- **Daily change** (close vs previous close) ≥ 10%, OR
- **Intraday change** (close vs open) ≥ 10%

Examples:
- ✅ Daily: +15.3% → Shows news analysis
- ✅ Daily: -11.2% → Shows news analysis
- ✅ Intraday: +12.5% → Shows news analysis
- ❌ Daily: +5.2% → No news analysis (< 10%)

## 🔍 Check Current Big Movers

Run this script on your EC2 instance to see if there are any big movers today:

```bash
cd /opt/ai-search
python3 check_big_movers.py
```

This will show you:
- How many stocks are currently being tracked
- Which stocks (if any) have ≥10% moves
- Whether those stocks have news analysis attached

## 🧪 Test the Feature (3 Methods)

### Method 1: Test Endpoint (Easiest)

We created a special test endpoint with mock big movers:

```bash
# On EC2, after pulling the latest code and restarting:
curl http://localhost:8000/api/test/big-movers | jq
```

Or visit in your browser:
```
http://YOUR_EC2_IP:8000/api/test/big-movers
```

This returns mock stocks with:
- 2 stocks with ≥10% moves (will have news analysis)
- 1 stock with normal move (no news analysis)

### Method 2: Create a Test Frontend Page

Create `frontend/test-news.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Test News Analysis</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect } = React;

        function TestNewsAnalysis() {
            const [stocks, setStocks] = useState([]);
            const [loading, setLoading] = useState(true);

            useEffect(() => {
                fetch('/api/test/big-movers')
                    .then(res => res.json())
                    .then(data => {
                        setStocks(data.stocks);
                        setLoading(false);
                    });
            }, []);

            if (loading) return <div>Loading...</div>;

            return (
                <div style={{ padding: '2rem' }}>
                    <h1>🔥 AI News Analysis - Test Mode</h1>
                    <p>This page shows mock big movers to demonstrate the feature</p>

                    {stocks.map(stock => (
                        <div key={stock.ticker} style={{
                            border: stock.news_analysis ? '2px solid #ff6b35' : '1px solid #ccc',
                            borderRadius: '12px',
                            padding: '1.5rem',
                            marginBottom: '1rem',
                            backgroundColor: '#fff'
                        }}>
                            <div>
                                <h3>{stock.name} ({stock.ticker})</h3>
                                {stock.news_analysis && (
                                    <span style={{
                                        background: 'linear-gradient(135deg, #ff6b35 0%, #f7931e 100%)',
                                        color: 'white',
                                        padding: '0.25rem 0.75rem',
                                        borderRadius: '6px',
                                        fontSize: '0.75rem',
                                        fontWeight: '700',
                                        marginLeft: '0.5rem'
                                    }}>
                                        🔥 Big Mover
                                    </span>
                                )}
                            </div>

                            <div style={{ marginTop: '1rem' }}>
                                <p><strong>Price:</strong> {stock.currency} {stock.current_price}</p>
                                <p><strong>Daily Change:</strong> {stock.change_percent.toFixed(2)}%</p>
                                <p><strong>Intraday Change:</strong> {stock.intraday_change_percent.toFixed(2)}%</p>
                            </div>

                            {stock.news_analysis && (
                                <div style={{
                                    marginTop: '1rem',
                                    padding: '1rem',
                                    background: 'linear-gradient(135deg, rgba(255, 107, 53, 0.05) 0%, rgba(247, 147, 30, 0.05) 100%)',
                                    borderLeft: '4px solid #ff6b35',
                                    borderRadius: '8px'
                                }}>
                                    <div style={{ fontWeight: '700', color: '#ff6b35', marginBottom: '0.5rem' }}>
                                        📰 Market Analysis
                                    </div>
                                    <p>{stock.news_analysis.analysis}</p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            );
        }

        ReactDOM.render(<TestNewsAnalysis />, document.getElementById('root'));
    </script>
</body>
</html>
```

Then visit: `http://YOUR_EC2_IP/test-news.html`

### Method 3: Wait for Real Big Movers

The feature will automatically appear when:
- **Market events**: FDA approvals, clinical trial results
- **Earnings surprises**: Better/worse than expected
- **Major news**: Partnerships, acquisitions, controversies
- **Analyst actions**: Significant upgrades/downgrades
- **Market crashes/rallies**: Sector-wide movements

## ✅ Verify Feature is Installed

Check that all components are in place:

```bash
cd /opt/ai-search

# 1. Check backend service exists
ls -la backend/app/services/stock_news_analysis.py

# 2. Check frontend component has the feature
grep -n "news_analysis" frontend/src/components/StockCard.jsx

# 3. Check API integration
grep -n "StockNewsAnalysisService" backend/app/api/routes/stocks.py

# 4. Test the service directly
python3 test_news_analysis.py
```

All of these should succeed if the feature is properly installed.

## 🔧 Deploy Test Endpoint to EC2

Run these commands on your EC2 instance:

```bash
# 1. Pull latest code (includes test endpoint)
cd /opt/ai-search
git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn

# 2. Restart backend
pm2 restart ai-search-backend

# 3. Wait a few seconds for restart
sleep 5

# 4. Test the endpoint
curl http://localhost:8000/api/test/big-movers | jq

# 5. Check if news analysis service is working
curl http://localhost:8000/api/test/check-news-service | jq
```

## 📊 What to Expect

### When Testing (Mock Data)
You'll see:
1. **2 stocks with orange borders** (≥10% moves)
2. **🔥 "Big Mover" badge** with pulse animation
3. **📰 Market Analysis section** with AI-generated text

### In Production (Real Data)
On most days:
- **0-3 stocks** might have ≥10% moves
- During major market events, you might see **5-10+** stocks
- The feature appears automatically, no configuration needed

## 🐛 Troubleshooting

### "I see the test data but not on real stocks"
✅ **This is normal!** Real stocks probably don't have ≥10% moves today.

### "Test endpoint returns error"
Check:
```bash
# Is backend running?
pm2 status

# Check logs
pm2 logs ai-search-backend --lines 50

# Test backend health
curl http://localhost:8000/api/health
```

### "news_analysis field is null/undefined"
Check:
```bash
# Verify OpenAI API key is set
grep OPENAI_API_KEY /opt/ai-search/.env

# Or check AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id openai-api-key
```

### "Frontend doesn't show the badge/analysis"
Check browser console:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for errors
4. Check Network tab - does API return `news_analysis` field?

## 📝 Summary

The feature **IS working** - it's just waiting for stocks to have big moves!

**Quick Test:**
```bash
# On EC2:
curl http://localhost:8000/api/test/big-movers | jq .stocks[0].news_analysis
```

This should return AI-generated news analysis for the mock stock.

**Production:**
The feature will light up automatically during market volatility. No action needed!
