#!/usr/bin/env python3
"""
Check if there are any stocks with big moves (≥10%) in the current data
This helps verify why you might not be seeing the news analysis feature
"""

import requests
import sys

def check_big_movers():
    """Check for stocks with significant moves"""

    print("=" * 80)
    print("🔍 Checking for Big Movers (≥10% change)")
    print("=" * 80)
    print()

    base_url = "http://localhost:8000"

    # Check if backend is running
    try:
        health_response = requests.get(f"{base_url}/api/health", timeout=5)
        print("✓ Backend is running")
        print()
    except requests.exceptions.RequestException as e:
        print(f"✗ Backend is not accessible at {base_url}")
        print(f"  Error: {str(e)}")
        print()
        print("Please make sure the backend is running:")
        print("  cd /opt/ai-search/backend")
        print("  uvicorn main:app --reload")
        print()
        return

    # Get HKEX stocks
    print("📊 Checking HKEX 18A Biotech stocks...")
    try:
        response = requests.get(f"{base_url}/api/stocks/prices", timeout=30)
        stocks = response.json()

        big_movers = []
        for stock in stocks:
            if stock.get('error'):
                continue

            daily_change = abs(stock.get('change_percent', 0))
            intraday_change = abs(stock.get('intraday_change_percent', 0))

            if daily_change >= 10 or intraday_change >= 10:
                big_movers.append({
                    'name': stock['name'],
                    'ticker': stock['ticker'],
                    'daily': stock.get('change_percent', 0),
                    'intraday': stock.get('intraday_change_percent', 0),
                    'has_news': 'news_analysis' in stock
                })

        print(f"  Total stocks: {len(stocks)}")
        print(f"  Big movers (≥10%): {len(big_movers)}")
        print()

        if big_movers:
            print("🔥 Big Movers Found:")
            print()
            for stock in big_movers:
                print(f"  {stock['name']} ({stock['ticker']})")
                print(f"    Daily: {stock['daily']:+.2f}%")
                print(f"    Intraday: {stock['intraday']:+.2f}%")
                print(f"    Has News Analysis: {'✓ YES' if stock['has_news'] else '✗ NO'}")
                print()
        else:
            print("📉 No big movers found in HKEX stocks today")
            print()
            print("This is why you don't see the news analysis feature!")
            print("The feature only appears when stocks move ≥10%")
            print()

    except Exception as e:
        print(f"  Error fetching HKEX stocks: {str(e)}")
        print()

    # Get Portfolio stocks
    print("💼 Checking Portfolio companies...")
    try:
        response = requests.get(f"{base_url}/api/stocks/portfolio", timeout=30)
        data = response.json()

        if data.get('success'):
            stocks = data.get('companies', [])

            big_movers = []
            for stock in stocks:
                if stock.get('error'):
                    continue

                daily_change = abs(stock.get('change_percent', 0))
                intraday_change = abs(stock.get('intraday_change_percent', 0))

                if daily_change >= 10 or intraday_change >= 10:
                    big_movers.append({
                        'name': stock['name'],
                        'ticker': stock['ticker'],
                        'daily': stock.get('change_percent', 0),
                        'intraday': stock.get('intraday_change_percent', 0),
                        'has_news': 'news_analysis' in stock
                    })

            print(f"  Total stocks: {len(stocks)}")
            print(f"  Big movers (≥10%): {len(big_movers)}")
            print()

            if big_movers:
                print("🔥 Big Movers Found:")
                print()
                for stock in big_movers:
                    print(f"  {stock['name']} ({stock['ticker']})")
                    print(f"    Daily: {stock['daily']:+.2f}%")
                    print(f"    Intraday: {stock['intraday']:+.2f}%")
                    print(f"    Has News Analysis: {'✓ YES' if stock['has_news'] else '✗ NO'}")
                    print()
            else:
                print("📉 No big movers found in portfolio stocks today")
                print()
    except Exception as e:
        print(f"  Error fetching portfolio stocks: {str(e)}")
        print()

    # Show test endpoint
    print("=" * 80)
    print("🧪 To See the Feature in Action")
    print("=" * 80)
    print()
    print("Use the test endpoint to see mock big movers with news analysis:")
    print(f"  {base_url}/api/test/big-movers")
    print()
    print("Or visit in browser:")
    print(f"  http://YOUR_EC2_IP:8000/api/test/big-movers")
    print()
    print("This shows what the feature looks like when stocks actually move ≥10%")
    print()


if __name__ == "__main__":
    check_big_movers()
