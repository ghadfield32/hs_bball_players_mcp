"""
Parse On3/Rivals HTML to Find Player Rankings Structure

Systematically parses the saved HTML file to identify
player rankings data and JSON embedded data.

Author: Claude Code
Date: 2025-11-15
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

def main():
    """Parse saved HTML and identify ranking data structure."""

    html_file = Path("data/debug/on3_rankings.html")

    if not html_file.exists():
        print(f"Error: HTML file not found at {html_file}")
        return

    print("="*60)
    print("Parsing On3/Rivals HTML for Rankings Data")
    print("="*60)
    print()

    html = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # Strategy 1: Look for JSON data embedded in scripts
    print("Strategy 1: Looking for embedded JSON data...")
    print("-"*60)

    scripts = soup.find_all('script', string=re.compile(r'rankings|players|recruits', re.I))
    print(f"Found {len(scripts)} script tags with ranking-related content")

    for i, script in enumerate(scripts[:5], 1):
        content = script.string
        if content and len(content) < 100000:  # Skip massive minified scripts
            print(f"\nScript {i} (first 300 chars):")
            print(content[:300])

            # Try to extract JSON objects
            json_matches = re.findall(r'\{[^{}]*"rank[^{}]*\}', content)
            if json_matches:
                print(f"  Found {len(json_matches)} potential JSON objects with 'rank'")

    print()

    # Strategy 2: Look for Next.js __NEXT_DATA__ JSON
    print("Strategy 2: Looking for Next.js __NEXT_DATA__...")
    print("-"*60)

    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    if next_data_script:
        print("SUCCESS: Found __NEXT_DATA__ script!")
        try:
            data = json.loads(next_data_script.string)

            # Save full JSON for inspection
            output_file = Path("data/debug/on3_next_data.json")
            output_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
            print(f"Saved full JSON to: {output_file}")

            # Try to find rankings data
            def find_rankings_recursive(obj, path=""):
                """Recursively search for rankings data."""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key

                        # Look for keys that might contain rankings
                        if any(keyword in key.lower() for keyword in ['rank', 'player', 'recruit', 'industry']):
                            print(f"\nFound key: {new_path}")
                            if isinstance(value, list) and len(value) > 0:
                                print(f"  Type: list with {len(value)} items")
                                print(f"  First item: {str(value[0])[:200]}")
                            elif isinstance(value, dict):
                                print(f"  Type: dict with keys: {list(value.keys())[:10]}")

                        find_rankings_recursive(value, new_path)

                elif isinstance(obj, list):
                    if len(obj) > 0 and isinstance(obj[0], dict):
                        # Check if this looks like a rankings list
                        first_item_keys = set(obj[0].keys())
                        ranking_keywords = {'rank', 'player', 'name', 'position', 'rating', 'stars'}

                        if len(first_item_keys & ranking_keywords) >= 2:
                            print(f"\n*** FOUND RANKINGS LIST at {path} ***")
                            print(f"  Length: {len(obj)} items")
                            print(f"  Keys: {list(first_item_keys)}")
                            print(f"  First item: {json.dumps(obj[0], indent=2)[:500]}")

            find_rankings_recursive(data)

        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse __NEXT_DATA__ JSON: {e}")
    else:
        print("ERROR: No __NEXT_DATA__ script found")

    print()

    # Strategy 3: Look for specific HTML patterns
    print("Strategy 3: Looking for HTML player elements...")
    print("-"*60)

    # Common patterns for player cards/rows
    patterns = [
        ("div", {"class": re.compile(r'player', re.I)}),
        ("div", {"class": re.compile(r'rank', re.I)}),
        ("tr", {"class": re.compile(r'player|rank', re.I)}),
        ("article", {}),
    ]

    for tag, attrs in patterns:
        elements = soup.find_all(tag, attrs, limit=3)
        if elements:
            print(f"\nFound {len(elements)} <{tag}> elements matching pattern")
            for i, elem in enumerate(elements[:2], 1):
                print(f"\nElement {i}:")
                print(f"  Classes: {elem.get('class', [])}")
                print(f"  Text content (first 200 chars): {elem.text.strip()[:200]}")
                print(f"  HTML (first 300 chars): {str(elem)[:300]}")

    print()
    print("="*60)
    print("PARSING COMPLETE")
    print("="*60)
    print()
    print("Check data/debug/on3_next_data.json for full Next.js data structure")


if __name__ == '__main__':
    main()
