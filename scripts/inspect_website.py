"""
Website Inspection Helper for Datasource Adapters

Helps inspect league websites to gather information needed for adapter implementation.
Provides a checklist-driven approach to documenting website structure.

Usage:
    python scripts/inspect_website.py

For EYBL fix:
    python scripts/inspect_website.py --adapter eybl

Author: Claude Code
Date: 2025-11-11
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    try:
        # Try to enable UTF-8 mode
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Emoji replacements for Windows compatibility
EMOJI_MAP = {
    '📋': '[INFO]',
    '🔍': '[SEARCH]',
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⚠️': '[WARN]',
    '🎯': '[TARGET]',
    '📊': '[TABLE]',
    '🏀': '[BBALL]',
    '💡': '[TIP]',
    '📝': '[NOTE]',
    '🔧': '[TOOL]',
    '🚀': '[ACTION]',
}

def safe_print(*args, **kwargs):
    """Print text with emoji handling for Windows."""
    # Convert all args to strings and handle emojis
    safe_args = []
    for arg in args:
        text = str(arg)
        if sys.platform == 'win32':
            # Replace emojis with ASCII on Windows
            for emoji, replacement in EMOJI_MAP.items():
                text = text.replace(emoji, replacement)
        safe_args.append(text)

    # Use built-in print with safe args
    import builtins
    builtins.print(*safe_args, **kwargs)

# Override print function globally for this script
print = safe_print

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.run(["pip", "install", "httpx", "beautifulsoup4"])
    import httpx
    from bs4 import BeautifulSoup


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"📋 {title}")
    print("=" * 70)


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


async def inspect_url(url: str, description: str = ""):
    """Inspect a URL and provide guidance."""
    print(f"\n🔍 Inspecting: {url}")
    if description:
        print(f"   Purpose: {description}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)

            if response.status_code == 200:
                print(f"✅ Status: {response.status_code} OK")

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Check for common table patterns
                tables = soup.find_all('table')
                print(f"📊 Found {len(tables)} table(s)")

                if tables:
                    print("\n🔎 Table Analysis:")
                    for i, table in enumerate(tables[:5], 1):  # Limit to first 5
                        print(f"\n  Table {i}:")

                        # Check for table classes/ids
                        table_class = table.get('class', [])
                        table_id = table.get('id', '')

                        if table_class:
                            print(f"    Classes: {', '.join(table_class)}")
                        if table_id:
                            print(f"    ID: {table_id}")

                        # Find headers
                        headers = []
                        thead = table.find('thead')
                        if thead:
                            header_cells = thead.find_all(['th', 'td'])
                            headers = [cell.get_text(strip=True) for cell in header_cells]
                        else:
                            # Try first row
                            first_row = table.find('tr')
                            if first_row:
                                header_cells = first_row.find_all(['th', 'td'])
                                if any(cell.name == 'th' for cell in header_cells):
                                    headers = [cell.get_text(strip=True) for cell in header_cells]

                        if headers:
                            print(f"    Headers ({len(headers)}): {', '.join(headers[:10])}")
                            if len(headers) > 10:
                                print(f"              ... and {len(headers) - 10} more")
                        else:
                            print("    Headers: None found")

                        # Count rows
                        tbody = table.find('tbody') or table
                        rows = tbody.find_all('tr')
                        print(f"    Rows: {len(rows)}")

                # Check for JavaScript rendering
                scripts = soup.find_all('script')
                has_react = any('react' in str(script).lower() for script in scripts)
                has_vue = any('vue' in str(script).lower() for script in scripts)
                has_angular = any('angular' in str(script).lower() for script in scripts)

                if has_react or has_vue or has_angular:
                    print("\n⚠️  JavaScript Framework Detected:")
                    if has_react:
                        print("    - React (may require browser rendering)")
                    if has_vue:
                        print("    - Vue (may require browser rendering)")
                    if has_angular:
                        print("    - Angular (may require browser rendering)")

                return soup

            elif response.status_code == 404:
                print(f"❌ Status: {response.status_code} NOT FOUND")
                print("   ⚠️  This URL doesn't exist. Need to find the correct path.")
                return None

            elif response.status_code >= 300 and response.status_code < 400:
                print(f"🔀 Status: {response.status_code} REDIRECT")
                print(f"   Redirected to: {response.url}")
                return None

            else:
                print(f"⚠️  Status: {response.status_code}")
                return None

    except httpx.TimeoutException:
        print("❌ Request timed out (30s)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def inspect_eybl():
    """Inspect EYBL website specifically."""
    print_section("EYBL Adapter Fix - Website Inspection")

    print("""
The EYBL adapter is currently broken because the website structure changed.
Let's inspect the website to understand what needs to be updated.

Current adapter expects:
  - URL: https://nikeeyb.com/cumulative-season-stats
  - Table with class containing 'stats'
  - Columns: Player, Team, Pos, GP, PPG, RPG, APG, etc.
""")

    # Try current URL
    print_subsection("Step 1: Check Current Stats URL")
    await inspect_url(
        "https://nikeeyb.com/cumulative-season-stats",
        "Current stats URL in adapter"
    )

    # Try alternative URLs
    print_subsection("Step 2: Try Alternative URLs")

    alternative_urls = [
        ("https://nikeeyb.com/stats", "Common stats path"),
        ("https://nikeeyb.com/statistics", "Alternative stats path"),
        ("https://nikeeyb.com/season-stats", "Season stats variation"),
        ("https://nikeeyb.com/players", "Players page"),
        ("https://nikeeyb.com/leaderboard", "Leaderboard page"),
        ("https://nikeeyb.com", "Home page (check for links)"),
    ]

    for url, desc in alternative_urls:
        await inspect_url(url, desc)
        await asyncio.sleep(1)  # Be polite

    # Provide manual inspection guidance
    print_subsection("Step 3: Manual Inspection")
    print("""
Please open https://nikeeyb.com in your browser and:

1. Find the Stats/Leaders page
   - Look for "Stats", "Leaders", "Statistics" in navigation
   - Note the actual URL

2. Open DevTools (F12) and inspect the stats table:
   - Right-click on the table -> Inspect
   - Note the table's class attribute (e.g., <table class="stats-table">)
   - Look for any data-* attributes

3. Check column headers:
   - Note exact column names: Player, Team, Pos, GP, PPG, etc.
   - Look for variations (e.g., "PTS/G" vs "PPG")

4. Check for JavaScript rendering:
   - View page source (Ctrl+U)
   - Search for <table> tag
   - If not found, page uses JavaScript rendering (more complex)

5. Test table extraction:
   - In DevTools Console, run: document.querySelectorAll('table')
   - This shows all tables on the page
""")

    print_subsection("Step 4: Update Adapter Code")
    print("""
Once you've identified the correct structure, update these in src/datasources/us/eybl.py:

1. Update stats_url (line ~33):
   self.stats_url = f"{self.base_url}/ACTUAL_PATH"

2. Update table finding logic (line ~120 in search_players):
   table = find_stat_table(soup, table_class_hint="ACTUAL_CLASS_NAME")

3. If column names changed, update mappings:
   - In parse_player_from_row() calls
   - In parse_season_stats_from_row() calls
   - In stat_column_map in get_leaderboard()

4. Test:
   pytest tests/test_datasources/test_eybl.py -v -s
""")


async def inspect_generic(url: str):
    """Inspect a generic website for adapter creation."""
    print_section("Generic Website Inspection")

    base_url = url.rstrip('/')

    print(f"\nInspecting: {base_url}")
    print("\nThis will check common paths for basketball stats websites.")

    # Try common paths
    paths_to_try = [
        ("/stats", "Statistics page"),
        ("/statistics", "Alternative statistics page"),
        ("/players", "Players page"),
        ("/leaderboard", "Leaderboard page"),
        ("/leaders", "Leaders page"),
        ("/teams", "Teams page"),
        ("/schools", "Schools page"),
        ("/schedule", "Schedule page"),
        ("/games", "Games page"),
        ("/standings", "Standings page"),
        ("", "Home page"),
    ]

    found_pages = []

    for path, description in paths_to_try:
        full_url = f"{base_url}{path}"
        soup = await inspect_url(full_url, description)
        if soup:
            found_pages.append((full_url, description))
        await asyncio.sleep(1)  # Be polite

    # Summary
    print_section("Summary")

    if found_pages:
        print("\n✅ Found the following pages:")
        for url, desc in found_pages:
            print(f"   - {url}")
            print(f"     ({desc})")
    else:
        print("\n⚠️  No pages found with common paths.")
        print("   You may need to navigate the website manually to find stats pages.")

    print("\n📋 Next Steps:")
    print("\n1. Visit the website in a browser")
    print("2. Navigate to find stats/players/teams pages")
    print("3. Note the URLs for each page type")
    print("4. Inspect table structure using DevTools")
    print("5. Use this information to create/update the adapter")
    print("\n6. Run adapter generator:")
    print("   python scripts/generate_adapter.py")


async def inspect_adapter_file(adapter_name: str):
    """Inspect an existing adapter file and suggest fixes."""
    print_section(f"{adapter_name.upper()} Adapter Inspection")

    # Find adapter file
    adapter_files = list(Path("src/datasources").rglob(f"{adapter_name}.py"))

    if not adapter_files:
        print(f"❌ Could not find adapter file for '{adapter_name}'")
        print(f"   Searched in: src/datasources/**/{adapter_name}.py")
        return

    adapter_path = adapter_files[0]
    print(f"📄 Found adapter: {adapter_path}")

    # Read adapter file
    content = adapter_path.read_text()

    # Extract URLs
    import re
    urls = re.findall(r'https?://[^\s"\']+', content)
    base_url_match = re.search(r'base_url\s*=\s*["\']([^"\']+)["\']', content)

    if base_url_match:
        base_url = base_url_match.group(1)
        print(f"\n🌐 Base URL: {base_url}")

        # Extract endpoint URLs
        stats_url_match = re.search(r'self\.stats_url\s*=\s*f?["\']([^"\']+)["\']', content)
        teams_url_match = re.search(r'self\.teams_url\s*=\s*f?["\']([^"\']+)["\']', content)
        schedule_url_match = re.search(r'self\.schedule_url\s*=\s*f?["\']([^"\']+)["\']', content)

        print("\n📍 Configured Endpoints:")
        if stats_url_match:
            stats_path = stats_url_match.group(1).replace('{self.base_url}', base_url).replace('${self.base_url}', base_url)
            print(f"   Stats: {stats_path}")
            await inspect_url(stats_path, "Stats endpoint")

        if teams_url_match:
            teams_path = teams_url_match.group(1).replace('{self.base_url}', base_url).replace('${self.base_url}', base_url)
            print(f"\n   Teams: {teams_path}")
            await inspect_url(teams_path, "Teams endpoint")

        if schedule_url_match:
            schedule_path = schedule_url_match.group(1).replace('{self.base_url}', base_url).replace('${self.base_url}', base_url)
            print(f"\n   Schedule: {schedule_path}")
            await inspect_url(schedule_path, "Schedule endpoint")

    else:
        print("⚠️  Could not extract base_url from adapter file")

    # Check for TODO comments
    todos = re.findall(r'#\s*TODO:?\s*(.+)', content, re.IGNORECASE)
    if todos:
        print("\n📝 TODO Items Found:")
        for i, todo in enumerate(todos[:10], 1):
            print(f"   {i}. {todo.strip()}")
        if len(todos) > 10:
            print(f"   ... and {len(todos) - 10} more")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Inspect league websites for adapter implementation"
    )
    parser.add_argument(
        "--adapter",
        help="Existing adapter to inspect (e.g., 'eybl', 'psal')"
    )
    parser.add_argument(
        "--url",
        help="URL of website to inspect for new adapter"
    )

    args = parser.parse_args()

    if args.adapter:
        if args.adapter.lower() == 'eybl':
            asyncio.run(inspect_eybl())
        else:
            asyncio.run(inspect_adapter_file(args.adapter.lower()))
    elif args.url:
        asyncio.run(inspect_generic(args.url))
    else:
        # Interactive mode
        print("=" * 70)
        print("🔍 Website Inspection Helper")
        print("=" * 70)
        print("\nWhat would you like to do?")
        print("\n1. Fix EYBL adapter (website structure changed)")
        print("2. Inspect existing adapter")
        print("3. Inspect website for new adapter")
        print("4. Exit")

        choice = input("\nChoice (1-4): ").strip()

        if choice == '1':
            asyncio.run(inspect_eybl())
        elif choice == '2':
            adapter_name = input("Adapter name (e.g., 'psal', 'mn_hub'): ").strip()
            asyncio.run(inspect_adapter_file(adapter_name))
        elif choice == '3':
            url = input("Website URL: ").strip()
            asyncio.run(inspect_generic(url))
        else:
            print("Goodbye!")


if __name__ == "__main__":
    main()
