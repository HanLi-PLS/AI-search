# 🔥 AI-Powered News Analysis for Big Movers

## Overview

The stock tracker automatically detects stocks with **significant price movements (≥ 10%)** and uses **OpenAI o4-mini with web search** to analyze the news and explain why the stock moved.

## ✨ Features

- **Automatic Detection**: Monitors both daily change (close vs previous close) AND intraday change (close vs open)
- **AI Analysis**: Uses o4-mini with web search to find and analyze recent news
- **Smart Caching**: Caches analysis per day to minimize API costs
- **Visual Indicators**:
  - 🔥 "Big Mover" badge with pulse animation
  - Orange border on stock cards
  - 📰 News analysis section with gradient background

## 📁 Implementation

### Backend

**Service**: `backend/app/services/stock_news_analysis.py`
```python
class StockNewsAnalysisService:
    def has_significant_move(self, stock_data: Dict[str, Any]) -> bool:
        """Check if stock has >= 10% daily or intraday change"""
        daily_change = abs(stock_data.get('change_percent', 0))
        intraday_change = abs(stock_data.get('intraday_change_percent', 0))
        return daily_change >= 10 or intraday_change >= 10

    def get_news_analysis(self, ticker: str, name: str, stock_data: Dict) -> Dict:
        """Fetch news analysis using OpenAI o4-mini with web search"""
        # Uses OpenAI to search web and analyze news
        # Caches result for the day
        # Returns analysis text
```

**API Integration**: `backend/app/api/routes/stocks.py`

Lines 878-885 (HKEX stocks):
```python
# Add news analysis for stocks with significant moves (>= 10%)
try:
    from backend.app.services.stock_news_analysis import StockNewsAnalysisService
    news_service = StockNewsAnalysisService()
    results = await asyncio.to_thread(news_service.process_stocks, list(results))
    logger.info(f"Processed {len(results)} stocks for news analysis")
except Exception as e:
    logger.error(f"Error adding news analysis: {str(e)}")
```

Lines 1448-1455 (Portfolio stocks):
```python
# Add news analysis for stocks with significant moves (>= 10%)
try:
    from backend.app.services.stock_news_analysis import StockNewsAnalysisService
    news_service = StockNewsAnalysisService()
    companies = await asyncio.to_thread(news_service.process_stocks, companies)
    logger.info(f"Processed {len(companies)} portfolio companies for news analysis")
except Exception as e:
    logger.error(f"Error adding news analysis to portfolio companies: {str(e)}")
```

### Frontend

**Component**: `frontend/src/components/StockCard.jsx`

Lines 49-58 (Badge):
```jsx
<div className={`stock-card ${stock.news_analysis ? 'has-news' : ''}`}>
  <div className="stock-header">
    <div>
      <h3>{stock.name}</h3>
      <span className="ticker">{stock.ticker}</span>
      {stock.news_analysis && (
        <span className="big-mover-badge" title="Significant price move (≥10%)">
          🔥 Big Mover
        </span>
      )}
    </div>
```

Lines 110-118 (News Section):
```jsx
{/* News Analysis for Big Movers */}
{stock.news_analysis && (
  <div className="news-analysis">
    <div className="news-header">
      <span className="news-icon">📰</span>
      <span className="news-title">Market Analysis</span>
    </div>
    <p className="news-content">{stock.news_analysis.analysis}</p>
  </div>
)}
```

**Styling**: `frontend/src/components/StockCard.css`

```css
/* Special border for stocks with news */
.stock-card.has-news {
  border: 2px solid #ff6b35;
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);
}

/* Animated badge */
.big-mover-badge {
  display: inline-block;
  background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  margin-left: 0.5rem;
  margin-top: 0.5rem;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 2px 6px rgba(255, 107, 53, 0.3);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.85;
    transform: scale(1.05);
  }
}

/* News analysis section */
.news-analysis {
  margin-top: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.05) 0%, rgba(247, 147, 30, 0.05) 100%);
  border-left: 4px solid #ff6b35;
  border-radius: 8px;
  animation: slideDown 0.3s ease;
}
```

## 🎯 How It Works

### Detection Logic

1. **Monitor Price Changes**: System checks every stock for significant moves
   ```
   Daily Change = (Today's Close - Yesterday's Close) / Yesterday's Close × 100
   Intraday Change = (Close - Open) / Open × 100
   ```

2. **Threshold**: If either change is ≥ 10% (absolute value), it's a "big mover"

3. **Examples**:
   - ✅ Daily: +15.3%, Intraday: +2.1% → BIG MOVER (daily ≥ 10%)
   - ✅ Daily: +3.2%, Intraday: -11.5% → BIG MOVER (intraday ≥ 10%)
   - ❌ Daily: +5.5%, Intraday: +4.2% → Normal (both < 10%)

### Analysis Process

1. **Check Cache**: First checks if analysis already exists for today
2. **Web Search**: If not cached, uses OpenAI o4-mini to:
   - Search for recent news about the company
   - Find press releases, regulatory filings, announcements
   - Analyze clinical trial results, approvals, financial reports
   - Check analyst reactions and market sentiment
3. **Generate Summary**: Creates 2-3 sentence analysis explaining:
   - What triggered the price movement
   - Key details about the trigger
   - Market reactions if available
4. **Cache Result**: Saves to local cache (and S3 if enabled)

### Caching System

- **Daily Cache**: `data/stock_news_cache/news_cache_YYYY-MM-DD.json`
- **TTL**: Cache is valid for the entire day
- **Benefits**:
  - Prevents duplicate API calls (saves costs)
  - Instant response for repeated requests
  - Historical record of analyses
- **Cleanup**: Old cache files are automatically backed up to S3 and removed

## 📊 Visual Examples

### Normal Stock (No Significant Move)
```
┌─────────────────────────────────────────────────┐
│ BeiGene (1801.HK)                               │
│ HKD 150.00                                      │
│ Daily: +3.75 (+2.5%)                            │
│ Intraday: +2.70 (+1.8%)                         │
│                                                 │
│ [No news analysis - changes < 10%]             │
└─────────────────────────────────────────────────┘
```

### Big Mover (With News Analysis)
```
┌─────────────────────────────────────────────────┐
│ Visen Pharmaceuticals (2561.HK)  🔥 Big Mover   │ ← Pulsing badge
│ HKD 25.50                                       │
│ Daily: +3.38 (+15.3%)                           │ ← Significant!
│ Intraday: +2.68 (+12.1%)                        │
│                                                 │
│ 📰 Market Analysis                              │ ← AI-generated
│ ╭─────────────────────────────────────────────╮ │
│ │ Visen Pharmaceuticals surged 15.3% following│ │
│ │ positive Phase II trial results announced   │ │
│ │ this morning. The company's lead candidate  │ │
│ │ met primary endpoints with strong safety    │ │
│ │ profile. Analysts raised price targets by   │ │
│ │ 20-30% following the announcement.          │ │
│ ╰─────────────────────────────────────────────╯ │
└─────────────────────────────────────────────────┘
   ↑ Orange border indicates big mover
```

## 🧪 Testing

Run the test script to see how it works:

```bash
python3 test_news_analysis.py
```

This will:
1. Test detection logic
2. Show examples of normal vs big mover stocks
3. Demonstrate the caching system
4. Show what appears in the frontend

## 💰 Cost Optimization

### Smart Caching
- Analysis is performed **once per day** per stock
- If a stock moves 15% and you refresh the page 100 times, only **1 API call** is made
- Cache is shared across all users

### Selective Analysis
- Only analyzes stocks with ≥ 10% moves
- On a typical day, maybe 0-3 stocks meet this threshold
- During market crashes or big news days, maybe 5-10 stocks

### Example Cost Calculation
```
Typical day:
- 66 HKEX stocks tracked
- 2 portfolio companies
- Total: 68 stocks

Big movers: 2 stocks (≈3% of stocks)
API calls: 2 × 1 = 2 calls/day
Cost: 2 × $0.10 = $0.20/day (o4-mini pricing)
Monthly: ≈$6/month
```

## 📈 Production Usage

### When You'll See It

The feature automatically activates when:
- Market opens/closes with significant events
- Clinical trial results are announced
- FDA approvals/rejections
- Major news or controversies
- Earnings surprises
- Analyst upgrades/downgrades

### What Users See

1. **Stock List Page**: Orange-bordered cards with 🔥 badge catch attention
2. **Hover Effect**: Enhanced shadow effect on big movers
3. **Analysis Box**: Prominent orange-accented section with news
4. **Badge Animation**: Subtle pulse effect draws the eye

## 🔧 Configuration

### Environment Variables

```bash
# Required for news analysis
OPENAI_API_KEY=sk-...
ONLINE_SEARCH_MODEL=o4-mini  # Model used for web search

# Optional: AWS for cache backup
USE_S3_STORAGE=true
AWS_S3_BUCKET=your-bucket-name
```

### Model Selection

Current: `o4-mini` (fast, cheap, has web search)
Alternatives:
- `gpt-4.1` - Faster but no built-in web search
- `o3` - More powerful but slower and more expensive

## 📝 Development Notes

### Adding More Analysis Types

You can extend the service to analyze:
- Volume spikes (>200% of average)
- Gap ups/downs (>5% pre-market move)
- Unusual options activity
- Institutional buying/selling

### Custom Thresholds

Edit `has_significant_move()` in `stock_news_analysis.py`:
```python
def has_significant_move(self, stock_data: Dict[str, Any]) -> bool:
    daily_change = abs(stock_data.get('change_percent', 0))
    intraday_change = abs(stock_data.get('intraday_change_percent', 0))

    # Customize threshold here (currently 10%)
    threshold = 10.0

    return daily_change >= threshold or intraday_change >= threshold
```

## ✅ Feature Status

- ✅ Backend service implemented
- ✅ API integration complete
- ✅ Frontend component with styling
- ✅ Caching system working
- ✅ S3 backup for historical data
- ✅ Automatic cleanup of old caches
- ✅ Error handling and fallbacks
- ✅ Works for both HKEX and Portfolio stocks

## 🚀 To See It In Action

1. **Start Backend**:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Wait for a Big Mover**:
   - The feature activates automatically
   - No manual intervention needed
   - Check stocks with recent news or events

4. **Or Create Test Data**:
   - Modify `get_all_prices()` to add mock big mover
   - Add `news_analysis` field manually for testing

---

**Last Updated**: 2025-11-15
**Status**: ✅ Production Ready
**Commit**: Latest on `claude/evaluate-html-to-react-0115LeSytewibig5d1F1A76B`
