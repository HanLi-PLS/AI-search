#!/bin/bash
echo "=========================================="
echo "Testing HTML File Size and Access"
echo "=========================================="

cd /opt/ai-search

echo ""
echo "Step 1: List HTML files in S3"
echo "------------------------------------------------------------"
aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/ --recursive | grep "\.html"

echo ""
echo ""
echo "Step 2: Check size of the specific HTML file"
echo "------------------------------------------------------------"
aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html --human-readable --summarize

echo ""
echo ""
echo "Step 3: Test reading HTML with Python (first 500 chars)"
echo "------------------------------------------------------------"
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/opt/ai-search/backend')

from app.services.ipo_data import IPODataService

service = IPODataService()
try:
    html = service.read_html_from_s3('public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html')
    print(f"✓ Successfully read HTML file")
    print(f"  Size: {len(html):,} characters ({len(html)/1024:.1f} KB)")
    print(f"  Preview: {html[:500]}")
except Exception as e:
    print(f"✗ Error: {e}")
PYTHON_EOF

echo ""
echo "=========================================="
