#!/usr/bin/env python3
"""
Standalone script to explore CapIQ schema and find correct data item IDs
Can be run directly on EC2: python scripts/explore_capiq_data_items.py
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    try:
        from app.services.capiq_data import get_capiq_service

        print("=" * 80)
        print("CapIQ Schema Exploration")
        print("=" * 80)
        print()

        service = get_capiq_service()

        if not service.available:
            print("ERROR: CapIQ service not available")
            print("Check Snowflake credentials in environment or AWS Secrets Manager")
            sys.exit(1)

        print("✓ Connected to CapIQ")
        print()

        # Run exploration for ticker 700 (Tencent)
        test_ticker = "700"
        print(f"Exploring data for test ticker: {test_ticker}")
        print()

        results = service.explore_schema_for_data_items(test_ticker)

        if "error" in results:
            print(f"ERROR: {results['error']}")
            sys.exit(1)

        # Print results in a readable format
        print("\n" + "=" * 80)
        print("PERIOD TYPES")
        print("=" * 80)
        for pt in results.get("period_types", []):
            print(f"  periodTypeId {pt['periodTypeId']:2d}: {pt['count']:,} records")

        print("\n  Common period types:")
        print("    1  = Annual")
        print("    2  = Quarterly")
        print("    8  = LTM (Last Twelve Months) - LIKELY THIS ONE FOR REVENUE")
        print()

        print("=" * 80)
        print("DATA ITEM IDs (first 30 of 1-200 range)")
        print("=" * 80)
        for di in results.get("data_items", [])[:30]:
            print(f"  dataItemId {di['dataItemId']:3d}: {di['count']:,} uses")
        print()

        print("=" * 80)
        print(f"REVENUE SAMPLES FOR TICKER {test_ticker}")
        print("=" * 80)
        samples = results.get("revenue_samples", [])
        if samples:
            print(f"Found {len(samples)} revenue samples:")
            for sample in samples[:20]:
                print(f"  periodType={sample['periodTypeId']}, "
                      f"dataItem={sample['dataItemId']}, "
                      f"periodEnd={sample['periodEndDate']}, "
                      f"value={sample['value']:,.0f}")
        else:
            print("  No revenue samples found")
        print()

        print("=" * 80)
        print(f"POTENTIAL IPO DATE DATA ITEMS FOR TICKER {test_ticker}")
        print("=" * 80)
        ipo_items = results.get("ipo_date_candidates", [])
        if ipo_items:
            print(f"Found {len(ipo_items)} potential date values:")
            for item in ipo_items[:20]:
                # Convert YYYYMMDD to readable format
                date_val = str(int(item['value']))
                if len(date_val) == 8:
                    formatted = f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}"
                    print(f"  dataItemId {item['dataItemId']:3d}: {formatted} (count={item['count']})")
                else:
                    print(f"  dataItemId {item['dataItemId']:3d}: {item['value']} (count={item['count']})")
        else:
            print("  No date-like values found")
        print()

        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()

        # Analyze results and make recommendations
        print("Based on the exploration:")
        print()

        # Check for LTM period type
        period_types = {pt['periodTypeId']: pt['count'] for pt in results.get("period_types", [])}
        if 8 in period_types:
            print("✓ periodTypeId = 8 exists (likely LTM) - USE THIS FOR REVENUE")
        elif 3 in period_types:
            print("✓ periodTypeId = 3 exists (possibly LTM) - TRY THIS FOR REVENUE")
        else:
            print("⚠ No obvious LTM period type found. Common values are 8 or 3.")
            print("  Available period types:", sorted(period_types.keys()))
        print()

        # Check for revenue data
        revenue_by_period = {}
        for sample in results.get("revenue_samples", []):
            period_id = sample['periodTypeId']
            if period_id not in revenue_by_period:
                revenue_by_period[period_id] = []
            revenue_by_period[period_id].append(sample)

        if revenue_by_period:
            print("Revenue data found for period types:", sorted(revenue_by_period.keys()))
            for period_id in sorted(revenue_by_period.keys()):
                count = len(revenue_by_period[period_id])
                print(f"  - periodTypeId {period_id}: {count} records")
        else:
            print("⚠ No revenue data found with dataItemId 1-5")
        print()

        # Check for IPO dates
        if ipo_items:
            most_common_item = max(ipo_items, key=lambda x: x['count'])
            print(f"Most common date dataItemId: {most_common_item['dataItemId']} "
                  f"(used {most_common_item['count']} times)")
            print("  This is LIKELY the IPO/listing date field")
        else:
            print("⚠ No IPO date candidates found in dataItemId 1-500 range")
        print()

        print("=" * 80)
        print("✓ Exploration complete")
        print("=" * 80)

    except ImportError as e:
        print(f"ERROR: Missing dependency - {e}")
        print("\nMake sure you're running from the backend directory:")
        print("  cd backend && python scripts/explore_capiq_data_items.py")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
