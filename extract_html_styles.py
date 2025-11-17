#!/usr/bin/env python3
"""
Extract and display the CSS styling from the HTML file
"""
import sys
sys.path.insert(0, '/home/user/AI-search/backend')

from backend.app.services.ipo_data import IPODataService
import re

service = IPODataService()

# Read the HTML file
html_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html"
html_content = service.read_html_from_s3(html_key)

# Extract the <style> section
style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)

if style_match:
    css_content = style_match.group(1)
    print("=" * 80)
    print("CSS Styling from Original HTML File")
    print("=" * 80)
    print(css_content)
    print("\n" + "=" * 80)
else:
    print("No <style> section found in HTML")

# Also show a snippet of the body content
body_match = re.search(r'<body>(.*?)</body>', html_content, re.DOTALL)
if body_match:
    body_snippet = body_match.group(1)[:1000]
    print("\nBody Content Preview (first 1000 chars):")
    print("=" * 80)
    print(body_snippet)
    print("=" * 80)
