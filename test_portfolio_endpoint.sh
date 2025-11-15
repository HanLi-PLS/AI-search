#!/bin/bash

echo "=========================================="
echo "Testing Portfolio Companies Endpoint"
echo "=========================================="
echo ""

# Test the endpoint
echo "Making request to: http://localhost:8000/api/stocks/portfolio"
echo ""

RESPONSE=$(curl -s http://localhost:8000/api/stocks/portfolio)

# Pretty print the response
echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "=========================================="
echo "Analysis"
echo "=========================================="

# Check if successful
SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('success', False))" 2>/dev/null)

if [ "$SUCCESS" = "True" ]; then
    echo "✓ API call successful"

    COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)
    echo "✓ Companies returned: $COUNT"

    # Check each company
    echo ""
    echo "Company details:"
    echo "$RESPONSE" | python3 << 'EOF'
import sys, json
data = json.load(sys.stdin)
for company in data.get('companies', []):
    print(f"\n{company['name']} ({company['ticker']}):")
    print(f"  Market: {company['market']}")
    print(f"  Data Source: {company.get('data_source', 'Unknown')}")
    if 'error' in company:
        print(f"  ❌ ERROR: {company['error']}")
    elif company.get('current_price'):
        print(f"  ✓ Price: ${company['current_price']:.2f}")
        if company.get('change_percent'):
            print(f"  ✓ Change: {company['change_percent']:.2f}%")
    else:
        print(f"  ⚠ No price data")
EOF
else
    echo "✗ API call failed"
    echo "Response: $RESPONSE"
fi

echo ""
echo "=========================================="
