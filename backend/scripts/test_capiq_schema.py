#!/usr/bin/env python3
"""
Test script to explore CapIQ schema and find correct data item IDs for:
- IPO/Listing Date (IQ_IPO_DATE mnemonic)
- LTM Revenue (IQ_TOTAL_REV with LTM period)
- Period types available
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.capiq_data import get_capiq_service

service = get_capiq_service()

if not service.available:
    print("CapIQ not available")
    sys.exit(1)

cursor = service.conn.cursor()

# Test 1: Check if there's a data item mapping table
print("=== Looking for data item mapping tables ===")
tables_query = """
SHOW TABLES LIKE '%DATAITEM%'
"""

try:
    cursor.execute(tables_query)
    results = cursor.fetchall()
    print(f"Found {len(results)} tables with 'DATAITEM':")
    for row in results:
        print(f"  - {row[1]}")  # Table name is usually in second column
except Exception as e:
    print(f"Error: {e}")

# Test 2: Check period types available
print("\n=== Checking period types ===")
period_query = """
SELECT DISTINCT periodTypeId, COUNT(*) as count
FROM ciqFinPeriod
GROUP BY periodTypeId
ORDER BY periodTypeId
LIMIT 20
"""

try:
    cursor.execute(period_query)
    results = cursor.fetchall()
    print("Period type IDs found:")
    for row in results:
        print(f"  periodTypeId = {row[0]}: {row[1]} records")
    print("\n  Note: periodTypeId = 1 is Annual")
    print("        periodTypeId = 2 is usually Quarterly")
    print("        Check if there's a periodTypeId for LTM (Last Twelve Months)")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Sample data item IDs
print("\n=== Searching for sample dataItemIds ===")
data_item_query = """
SELECT DISTINCT dataItemId, COUNT(*) as usage_count
FROM ciqFinCollectionData
WHERE dataItemId BETWEEN 1 AND 100
GROUP BY dataItemId
ORDER BY dataItemId
LIMIT 30
"""

try:
    cursor.execute(data_item_query)
    results = cursor.fetchall()
    print(f"Sample dataItemIds (1-100) and their usage:")
    for row in results:
        print(f"  dataItemId = {row[0]}: used {row[1]} times")
    print("\n  dataItemId = 1 should be IQ_TOTAL_REV (Total Revenue)")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Try to find a company with revenue data
print("\n=== Testing revenue query for a known company (ticker 700 - Tencent) ===")
test_revenue_query = """
SELECT
    fp.companyId,
    fp.periodTypeId,
    fi.periodEndDate,
    fcd.dataItemId,
    fcd.dataItemValue as revenue
FROM ciqFinPeriod fp
INNER JOIN ciqFinInstance fi ON fp.financialPeriodId = fi.financialPeriodId
INNER JOIN ciqFinInstanceToCollection fitc ON fi.financialInstanceId = fitc.financialInstanceId
INNER JOIN ciqFinCollection fc ON fitc.financialCollectionId = fc.financialCollectionId
INNER JOIN ciqFinCollectionData fcd ON fc.financialCollectionId = fcd.financialCollectionId
INNER JOIN ciqCompany c ON fp.companyId = c.companyId
INNER JOIN ciqSecurity sec ON c.companyId = sec.companyId
INNER JOIN ciqTradingItem ti ON sec.securityId = ti.securityId
WHERE UPPER(ti.tickerSymbol) = '700'
    AND fcd.dataItemId = 1  -- IQ_TOTAL_REV
    AND fp.periodTypeId IN (1, 2)  -- Annual or Quarterly
    AND fi.latestForFinancialPeriodFlag = 1
    AND fcd.dataItemValue IS NOT NULL
ORDER BY fi.periodEndDate DESC
LIMIT 5
"""

try:
    cursor.execute(test_revenue_query)
    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} revenue records for ticker 700:")
        for row in results:
            print(f"  companyId={row[0]}, periodType={row[1]}, periodEnd={row[2]}, dataItemId={row[3]}, revenue={row[4]}")
    else:
        print("  No revenue data found for ticker 700 with dataItemId=1")
        print("  This might mean dataItemId=1 is not the correct ID for revenue,")
        print("  or the company doesn't have revenue data in CapIQ")
except Exception as e:
    print(f"Error: {e}")

cursor.close()
print("\n✓ Test complete")
print("\nNext steps:")
print("1. Check if periodTypeId for LTM exists (might be 3, 4, or another number)")
print("2. Verify dataItemId=1 returns revenue data")
print("3. Look for data item mapping table to find IQ_IPO_DATE")
