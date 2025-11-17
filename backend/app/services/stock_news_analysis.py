"""
Service for analyzing significant stock price moves using OpenAI o4-mini web search
Detects stocks with >= 10% daily or intraday change and fetches news analysis
"""
import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional
from pathlib import Path
import openai
from backend.app.config import settings

logger = logging.getLogger(__name__)


class StockNewsAnalysisService:
    """Service for analyzing significant stock price movements"""

    def __init__(self):
        self.openai_api_key = settings.get_openai_api_key()
        openai.api_key = self.openai_api_key

        # Cache storage
        self.cache_dir = settings.DATA_DIR / "stock_news_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Current cache file (date-based)
        self.today = date.today()
        self.cache_file = self.cache_dir / f"news_cache_{self.today.isoformat()}.json"

        # Load cache if exists
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file if it exists for today"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    logger.info(f"Loaded news cache from {self.cache_file} with {len(cache_data)} entries")
                    return cache_data
            except Exception as e:
                logger.error(f"Error loading cache from {self.cache_file}: {str(e)}")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved news cache to {self.cache_file} with {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Error saving cache to {self.cache_file}: {str(e)}")

    def _backup_cache_to_s3(self):
        """Backup cache to S3 when date changes"""
        if not settings.USE_S3_STORAGE or not settings.AWS_S3_BUCKET:
            logger.info("S3 storage not enabled, skipping cache backup")
            return

        try:
            from backend.app.services.s3_storage import S3StockDataService
            s3_service = S3StockDataService()

            # Upload cache file to S3
            s3_key = f"stock_news_cache/{self.today.isoformat()}.json"

            with open(self.cache_file, 'rb') as f:
                s3_service.s3_client.put_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType='application/json'
                )

            logger.info(f"Backed up news cache to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Error backing up cache to S3: {str(e)}")

    def _clean_old_cache_files(self):
        """Remove cache files older than today and backup to S3"""
        try:
            for cache_file in self.cache_dir.glob("news_cache_*.json"):
                # Extract date from filename
                filename = cache_file.stem
                file_date_str = filename.replace("news_cache_", "")

                try:
                    file_date = date.fromisoformat(file_date_str)

                    # If older than today, backup to S3 and delete
                    if file_date < self.today:
                        logger.info(f"Cleaning up old cache file: {cache_file}")

                        # Backup to S3 first
                        if settings.USE_S3_STORAGE and settings.AWS_S3_BUCKET:
                            try:
                                from backend.app.services.s3_storage import S3StockDataService
                                s3_service = S3StockDataService()

                                s3_key = f"stock_news_cache/{file_date_str}.json"
                                with open(cache_file, 'rb') as f:
                                    s3_service.s3_client.put_object(
                                        Bucket=settings.AWS_S3_BUCKET,
                                        Key=s3_key,
                                        Body=f.read(),
                                        ContentType='application/json'
                                    )
                                logger.info(f"Backed up old cache to S3: {s3_key}")
                            except Exception as e:
                                logger.warning(f"Failed to backup {cache_file} to S3: {str(e)}")

                        # Delete local file
                        cache_file.unlink()
                        logger.info(f"Deleted old cache file: {cache_file}")
                except ValueError:
                    logger.warning(f"Could not parse date from filename: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning old cache files: {str(e)}")

    def has_significant_move(self, stock_data: Dict[str, Any]) -> bool:
        """
        Check if stock has significant price movement (>= 10%)

        Args:
            stock_data: Stock data dictionary with change_percent and intraday_change_percent

        Returns:
            True if either daily or intraday change >= 10%
        """
        daily_change = abs(stock_data.get('change_percent', 0))
        intraday_change = abs(stock_data.get('intraday_change_percent', 0))

        return daily_change >= 10 or intraday_change >= 10

    def get_news_analysis(self, ticker: str, name: str, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get news analysis for a stock with significant price movement

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            name: Company name
            stock_data: Stock data dictionary

        Returns:
            Dictionary with news analysis or None if not a significant move
        """
        # Check if significant move
        if not self.has_significant_move(stock_data):
            return None

        # Get trade date from stock data (fallback to today if not available)
        trade_date_str = stock_data.get('trade_date')
        if trade_date_str:
            # Handle both string and datetime formats
            if isinstance(trade_date_str, str):
                # Extract just the date part if it's ISO format with time
                trade_date_str = trade_date_str.split('T')[0]
        else:
            trade_date_str = date.today().isoformat()
            logger.warning(f"No trade_date found for {ticker}, using today: {trade_date_str}")

        # Use ticker + trade_date as cache key to handle same ticker on different dates
        cache_key = f"{ticker}_{trade_date_str}"

        # Check cache first
        if cache_key in self.cache:
            logger.info(f"Using cached news analysis for {ticker} on {trade_date_str}")
            return self.cache[cache_key]

        # Fetch news analysis using OpenAI o4-mini
        try:
            analysis = self._fetch_news_analysis(ticker, name, stock_data, trade_date_str)

            # Cache the result with trade_date in key
            self.cache[cache_key] = analysis
            self._save_cache()

            return analysis
        except Exception as e:
            logger.error(f"Error fetching news analysis for {ticker}: {str(e)}")
            return None

    def _fetch_news_analysis(self, ticker: str, name: str, stock_data: Dict[str, Any], trade_date_str: str) -> Dict[str, Any]:
        """
        Fetch news analysis using OpenAI o4-mini with web search

        Args:
            ticker: Stock ticker
            name: Company name
            stock_data: Stock data dictionary
            trade_date_str: The actual date of the price movement (YYYY-MM-DD)

        Returns:
            Dictionary with analysis results
        """
        daily_change = stock_data.get('change_percent', 0)
        intraday_change = stock_data.get('intraday_change_percent', 0)
        current_price = stock_data.get('current_price', 0)
        currency = stock_data.get('currency', 'HKD')

        # Parse trade date to create a search window
        try:
            from datetime import timedelta
            trade_date = datetime.fromisoformat(trade_date_str).date()
            # Search for news from 2 days before to the trade date
            search_start = trade_date - timedelta(days=2)
            search_end = trade_date

            date_context = f"on {trade_date.strftime('%B %d, %Y')} (search news from {search_start.strftime('%B %d')} to {search_end.strftime('%B %d, %Y')})"
        except:
            # Fallback if date parsing fails
            date_context = f"on {trade_date_str}"

        # Construct prompt for o4-mini with specific date context
        prompt = f"""Search for news and information about {name} (ticker: {ticker}) to analyze the reason for its significant price movement {date_context}.

Stock Information:
- Company: {name}
- Ticker: {ticker}
- Price on {trade_date_str}: {currency} {current_price:.2f}
- Daily Change: {daily_change:+.2f}%
- Intraday Change: {intraday_change:+.2f}%

Please search for news, press releases, regulatory filings, or other relevant information from around {date_context} that might explain this significant price movement.

Provide a concise analysis (2-3 sentences) covering:
1. What triggered this price movement (specific news, events, or announcements)
2. Key details about the trigger (e.g., clinical trial results, regulatory approval, financial results)
3. Market sentiment or analyst reactions if available

Focus on factual information from credible sources from the specified time period. If no specific news is found from that period, mention that and provide possible general reasons."""

        try:
            # Use o4-mini with web search tool
            logger.info(f"Fetching news analysis for {ticker} ({name}) using o4-mini with web search")

            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)

            response = client.responses.create(
                model=settings.ONLINE_SEARCH_MODEL,  # o4-mini
                tools=[{
                    "type": "web_search",
                    "search_context_size": "high"
                }],
                input=prompt
            )

            analysis_text = response.output_text.strip()

            result = {
                "ticker": ticker,
                "name": name,
                "analysis": analysis_text,
                "daily_change": daily_change,
                "intraday_change": intraday_change,
                "timestamp": datetime.now().isoformat(),
                "date": trade_date_str  # Use actual trade date, not today
            }

            logger.info(f"Successfully fetched news analysis for {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error calling OpenAI API for {ticker}: {str(e)}")
            raise

    def process_stocks(self, stocks: list) -> list:
        """
        Process a list of stocks and add news analysis for significant movers

        Args:
            stocks: List of stock data dictionaries

        Returns:
            List of stocks with news_analysis field added where applicable
        """
        # Clean old cache files on first run of the day
        self._clean_old_cache_files()

        for stock in stocks:
            ticker = stock.get('ticker')
            name = stock.get('name')

            if not ticker or not name:
                continue

            # Get news analysis if significant move
            analysis = self.get_news_analysis(ticker, name, stock)

            if analysis:
                stock['news_analysis'] = analysis
                logger.info(f"Added news analysis to {ticker} ({name})")

        return stocks

    def clear_cache(self):
        """Clear current cache (used for testing or manual refresh)"""
        self.cache = {}
        self._save_cache()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "date": self.today.isoformat(),
            "entries": len(self.cache),
            "cache_file": str(self.cache_file),
            "tickers": list(self.cache.keys())
        }
