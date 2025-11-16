"""
Parse ANGT API JSON Response

Analyzes the structure of the JSON response from the ANGT API endpoint.

Usage:
    python scripts/parse_angt_api_json.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - ANGT API Analysis
"""

import json
from pathlib import Path

json_file = Path(__file__).parent.parent / "data" / "debug" / "angt_players_api.json"

print("=" * 80)
print("ANGT API JSON STRUCTURE ANALYSIS")
print("=" * 80)

# Read JSON
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\nTop-level keys: {list(data.keys())}")

# Navigate to find player data
if 'pageProps' in data:
    page_props = data['pageProps']
    print(f"\npageProps keys: {list(page_props.keys())}")

    # Look for player data
    for key in page_props:
        val = page_props[key]
        if isinstance(val, list):
            print(f"\n{key}: List with {len(val)} items")
            if len(val) > 0 and isinstance(val[0], dict):
                print(f"  First item keys: {list(val[0].keys())}")
                print(f"\n  Sample player:")
                for k, v in list(val[0].items())[:15]:  # First 15 fields
                    print(f"    {k}: {v}")
        elif isinstance(val, dict):
            print(f"\n{key}: Dict with {len(val)} keys")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
