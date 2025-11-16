"""
Extract JSON data from ANGT stats page

The ANGT page is a Next.js app that embeds data in a __NEXT_DATA__ script tag.
This script extracts that JSON to understand the data structure.

Usage:
    python scripts/extract_angt_json.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - ANGT Debugging
"""

import json
import re
from pathlib import Path

html_file = Path(__file__).parent.parent / "data" / "debug" / "angt_stats.html"
output_file = Path(__file__).parent.parent / "data" / "debug" / "angt_next_data.json"

print("=" * 80)
print("ANGT JSON DATA EXTRACTION")
print("=" * 80)

if not html_file.exists():
    print(f"\nERROR: HTML file not found: {html_file}")
    print("Run: python scripts/debug_angt_page.py first")
    exit(1)

print(f"\nReading: {html_file}")

# Read HTML
html = html_file.read_text(encoding='utf-8')

# Find __NEXT_DATA__ script tag
pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
match = re.search(pattern, html, re.DOTALL)

if match:
    json_text = match.group(1)
    print(f"\nFound __NEXT_DATA__ (length: {len(json_text)} characters)")

    # Parse JSON
    try:
        data = json.loads(json_text)

        # Save to file
        output_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f"Saved JSON to: {output_file}")

        # Analyze structure
        print("\n" + "=" * 80)
        print("JSON STRUCTURE ANALYSIS")
        print("=" * 80)

        # Check for player data
        if 'props' in data and 'pageProps' in data['props']:
            page_props = data['props']['pageProps']
            print(f"\nPage Props keys: {list(page_props.keys())}")

            # Look for stats/players data
            for key in page_props:
                val = page_props[key]
                if isinstance(val, list) and len(val) > 0:
                    print(f"\n{key}: List with {len(val)} items")
                    if len(val) > 0:
                        print(f"  First item keys: {list(val[0].keys()) if isinstance(val[0], dict) else type(val[0])}")
                elif isinstance(val, dict):
                    print(f"\n{key}: Dict with keys: {list(val.keys())}")

        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\nNext: Inspect {output_file} to find player stats structure")

    except json.JSONDecodeError as e:
        print(f"\nERROR: Failed to parse JSON: {e}")
        print("Saving raw JSON text anyway...")
        output_file.write_text(json_text, encoding='utf-8')
else:
    print("\nNO __NEXT_DATA__ found in HTML!")
    print("This page may load data via AJAX after initial render.")
    print("\nSearching for other JSON structures...")

    # Search for other common patterns
    patterns = [
        (r'window\.__INITIAL_STATE__\s*=\s*({.*?});', 'window.__INITIAL_STATE__'),
        (r'window\.APP_DATA\s*=\s*({.*?});', 'window.APP_DATA'),
    ]

    for pattern, name in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"Found: {name}")
            try:
                data = json.loads(match.group(1))
                output_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
                print(f"Saved to: {output_file}")
            except:
                print(f"Failed to parse {name}")
