#!/usr/bin/env python
"""
Wisconsin WIAA Fixture Browser Helper

Human-in-the-loop browser opener that automates URL generation and browser
launching while respecting WIAA's bot protection. This script eliminates
context switching and manual URL construction during fixture downloads.

**Why This Approach:**
WIAA's website blocks automated HTTP requests (403 errors), which is their
explicit signal to prevent bot access. This script respects that protection
by keeping a human in the loop while automating everything around the download:
- URL construction
- Browser opening
- File naming guidance
- Progress tracking

Usage:
    # Open browsers for all planned fixtures
    python scripts/open_missing_wiaa_fixtures.py --planned

    # Only Priority 1 fixtures (2024 remaining)
    python scripts/open_missing_wiaa_fixtures.py --priority 1

    # Specific year
    python scripts/open_missing_wiaa_fixtures.py --year 2024

    # Specific fixtures
    python scripts/open_missing_wiaa_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"

    # Auto-validate after downloading (runs process_fixtures.py when done)
    python scripts/open_missing_wiaa_fixtures.py --planned --auto-validate

    # Batch mode (open multiple tabs before waiting)
    python scripts/open_missing_wiaa_fixtures.py --planned --batch-size 5

Workflow:
    1. Reads manifest_wisconsin.yml to find missing fixtures
    2. Filters based on command-line flags (planned/priority/year/specific)
    3. For each missing fixture:
       a. Constructs the WIAA URL
       b. Opens URL in your default browser
       c. Shows the exact filename to use when saving
       d. Waits for you to save the HTML file
       e. Verifies the file was saved (optional check)
    4. Generates summary report
    5. Optionally runs process_fixtures.py to validate and update manifest

Benefits:
    - Zero manual URL construction or copy/paste
    - Correct filenames shown upfront (prevents naming errors)
    - Progress tracking (shows X of Y remaining)
    - Batch mode for efficiency
    - Optional auto-validation when downloads complete
    - Respects WIAA's bot protection (no HTTP requests)
"""

import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import yaml

# Paths
FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"

# WIAA URL pattern
BASE_URL = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/"


class FixtureBrowserHelper:
    """
    Browser helper for downloading Wisconsin WIAA fixtures.

    This class implements a human-in-the-loop workflow that:
    - Identifies missing fixtures from the manifest
    - Opens browser tabs to the correct WIAA URLs
    - Guides the user on exact filenames to use
    - Tracks progress through the download session
    - Optionally triggers validation after downloads complete
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the browser helper.

        Args:
            verbose: If True, show detailed progress messages
        """
        self.verbose = verbose
        self.manifest = self._load_manifest()
        self.stats = {
            "opened": 0,
            "saved": 0,
            "skipped": 0,
            "already_present": 0
        }

    def _load_manifest(self) -> dict:
        """Load the fixture manifest from YAML file."""
        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"Manifest not found: {MANIFEST_PATH}\n"
                "Make sure you're running this script from the repository root."
            )

        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_fixture_path(self, year: int, gender: str, division: str) -> Path:
        """Get the expected fixture file path."""
        return FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"

    def _construct_url(self, year: int, gender: str, division: str) -> str:
        """Construct WIAA URL for a given fixture."""
        filename = f"{year}_Basketball_{gender}_{division}.html"
        return BASE_URL + filename

    def get_missing_fixtures(
        self,
        planned_only: bool = False,
        priority: Optional[int] = None,
        year: Optional[int] = None,
        specific_fixtures: Optional[List[Tuple[int, str, str]]] = None
    ) -> List[Dict[str, any]]:
        """
        Get list of missing fixtures based on filters.

        Args:
            planned_only: If True, only return fixtures with status="planned"
            priority: If set, only return fixtures with matching priority (1 or 2)
            year: If set, only return fixtures from this year
            specific_fixtures: If set, only return these specific fixtures
                              Format: [(year, gender, division), ...]

        Returns:
            List of dicts with fixture info:
            {
                "year": 2024,
                "gender": "Boys",
                "division": "Div2",
                "url": "https://...",
                "filename": "2024_Basketball_Boys_Div2.html",
                "status": "planned",
                "priority": 1
            }
        """
        missing = []

        for entry in self.manifest.get("fixtures", []):
            year_val = entry["year"]
            gender_val = entry["gender"]
            division_val = entry["division"]
            status = entry.get("status", "")

            # Apply filters
            if planned_only and status != "planned":
                continue

            if priority is not None and entry.get("priority") != priority:
                continue

            if year is not None and year_val != year:
                continue

            if specific_fixtures is not None:
                if (year_val, gender_val, division_val) not in specific_fixtures:
                    continue

            # Check if file exists
            file_path = self._get_fixture_path(year_val, gender_val, division_val)
            if file_path.exists():
                self.stats["already_present"] += 1
                continue

            # Add to missing list
            missing.append({
                "year": year_val,
                "gender": gender_val,
                "division": division_val,
                "url": self._construct_url(year_val, gender_val, division_val),
                "filename": file_path.name,
                "status": status,
                "priority": entry.get("priority")
            })

        return missing

    def open_fixture_in_browser(
        self,
        fixture: Dict[str, any],
        index: int,
        total: int,
        batch_mode: bool = False
    ) -> bool:
        """
        Open a single fixture in the browser and wait for user to save it.

        Args:
            fixture: Fixture info dict
            index: Current fixture index (1-based)
            total: Total number of fixtures to process
            batch_mode: If True, open multiple browsers before waiting

        Returns:
            True if user confirmed save, False if skipped
        """
        year = fixture["year"]
        gender = fixture["gender"]
        division = fixture["division"]
        url = fixture["url"]
        filename = fixture["filename"]

        print(f"\n{'='*80}")
        print(f"Fixture {index}/{total}: {year} {gender} {division}")
        print(f"{'='*80}")
        print(f"URL: {url}")
        print(f"Save as: {filename}")
        print(f"Save location: {FIXTURES_DIR.resolve()}")
        print()

        # Open browser
        try:
            webbrowser.open(url)
            self.stats["opened"] += 1
            print("✅ Opened in browser")
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")
            print(f"   Please manually navigate to: {url}")

        if batch_mode:
            # In batch mode, don't wait - just open and continue
            return True

        # Wait for user to save the file
        print()
        print("Instructions:")
        print("  1. In your browser, use 'Save Page As...' or Ctrl+S / Cmd+S")
        print("  2. Choose format: 'Webpage, HTML Only' (NOT 'Complete')")
        print(f"  3. Save to: {FIXTURES_DIR.resolve()}")
        print(f"  4. Use filename: {filename}")
        print()

        while True:
            response = input("Press ENTER when saved, 's' to skip, 'q' to quit: ").strip().lower()

            if response == 'q':
                print("\n🛑 Quitting...")
                sys.exit(0)

            elif response == 's':
                print("⏭️  Skipped")
                self.stats["skipped"] += 1
                return False

            elif response == '':
                # Check if file was actually saved
                file_path = self._get_fixture_path(year, gender, division)
                if file_path.exists():
                    print(f"✅ Confirmed: {filename} exists")
                    self.stats["saved"] += 1
                    return True
                else:
                    print(f"⚠️  Warning: {filename} not found in {FIXTURES_DIR}")
                    retry = input("   Continue anyway? (y/N): ").strip().lower()
                    if retry == 'y':
                        self.stats["saved"] += 1
                        return True
                    else:
                        print("   Waiting for file...")
            else:
                print("Invalid input. Press ENTER when saved, 's' to skip, 'q' to quit.")

    def process_batch(
        self,
        fixtures: List[Dict[str, any]],
        batch_size: int = 1
    ) -> None:
        """
        Process a batch of fixtures.

        Args:
            fixtures: List of fixture dicts to process
            batch_size: Number of browsers to open before pausing (1 = interactive)
        """
        if not fixtures:
            print("\n✅ No missing fixtures found!")
            print(f"   {self.stats['already_present']} fixtures already present")
            return

        total = len(fixtures)
        print(f"\n📋 Found {total} missing fixture(s) to download")
        print(f"   {self.stats['already_present']} fixture(s) already present")
        print()

        if batch_size > 1:
            print(f"🚀 Batch mode: Opening {batch_size} tabs at a time")
            print()

        # Process fixtures
        for i, fixture in enumerate(fixtures, 1):
            is_batch = batch_size > 1 and i % batch_size != 0 and i != total
            self.open_fixture_in_browser(fixture, i, total, batch_mode=is_batch)

            # If batch mode and we've opened batch_size tabs, pause
            if batch_size > 1 and (i % batch_size == 0 or i == total):
                print(f"\n⏸️  Opened {min(i, total)} / {total} tabs")
                print("   Save all open tabs, then press ENTER to continue...")
                input()

                # Verify saved files
                start_idx = max(0, i - batch_size)
                for j in range(start_idx, i):
                    f = fixtures[j]
                    file_path = self._get_fixture_path(f["year"], f["gender"], f["division"])
                    if file_path.exists():
                        print(f"   ✅ {f['filename']}")
                        self.stats["saved"] += 1
                    else:
                        print(f"   ⚠️  {f['filename']} - not found")

    def print_summary(self) -> None:
        """Print session summary."""
        print(f"\n{'='*80}")
        print("SESSION SUMMARY")
        print(f"{'='*80}")
        print(f"Browsers opened: {self.stats['opened']}")
        print(f"Files saved:     {self.stats['saved']}")
        print(f"Skipped:         {self.stats['skipped']}")
        print(f"Already present: {self.stats['already_present']}")
        print()

        if self.stats["saved"] > 0:
            print("✅ Next step: Validate and update manifest")
            print("   Run: python scripts/process_fixtures.py --planned")
            print()
        elif self.stats["skipped"] > 0:
            print("ℹ️  Some fixtures were skipped")
            print("   Re-run this command to download skipped fixtures")
            print()


def parse_fixtures(fixture_strings: List[str]) -> List[Tuple[int, str, str]]:
    """
    Parse fixture strings into tuples.

    Args:
        fixture_strings: List of strings like "2024,Boys,Div2"

    Returns:
        List of (year, gender, division) tuples
    """
    fixtures = []
    for s in fixture_strings:
        parts = s.split(",")
        if len(parts) != 3:
            raise ValueError(f"Invalid fixture format: {s}. Expected: YEAR,GENDER,DIVISION")

        year = int(parts[0].strip())
        gender = parts[1].strip()
        division = parts[2].strip()
        fixtures.append((year, gender, division))

    return fixtures


def main():
    parser = argparse.ArgumentParser(
        description="Open browser tabs for missing Wisconsin WIAA fixtures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all planned fixtures
  python scripts/open_missing_wiaa_fixtures.py --planned

  # Only Priority 1 fixtures (2024 remaining)
  python scripts/open_missing_wiaa_fixtures.py --priority 1

  # Only 2024 fixtures
  python scripts/open_missing_wiaa_fixtures.py --year 2024

  # Specific fixtures
  python scripts/open_missing_wiaa_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"

  # Batch mode (open 5 tabs at once)
  python scripts/open_missing_wiaa_fixtures.py --planned --batch-size 5

  # Auto-validate after downloading
  python scripts/open_missing_wiaa_fixtures.py --planned --auto-validate

Notes:
  - This script opens URLs in your browser; you must manually save the HTML
  - Use "Save Page As... → HTML Only" (NOT "Complete")
  - Save files to: tests/fixtures/wiaa/
  - Use exact filename shown by the script
  - After downloading, run: python scripts/process_fixtures.py --planned
        """
    )

    parser.add_argument(
        "--planned",
        action="store_true",
        help="Process all fixtures with status='planned'"
    )
    parser.add_argument(
        "--priority",
        type=int,
        choices=[1, 2],
        help="Only process fixtures with this priority (1 or 2)"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Only process fixtures from this year"
    )
    parser.add_argument(
        "--fixtures",
        nargs="+",
        help="Specific fixtures to process (format: 'YEAR,GENDER,DIVISION')"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of browser tabs to open before pausing (default: 1)"
    )
    parser.add_argument(
        "--auto-validate",
        action="store_true",
        help="Run process_fixtures.py after downloads complete"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.planned, args.priority, args.year, args.fixtures]):
        parser.error("Must specify at least one of: --planned, --priority, --year, --fixtures")

    # Initialize helper
    helper = FixtureBrowserHelper(verbose=not args.quiet)

    # Get missing fixtures
    specific_fixtures = None
    if args.fixtures:
        specific_fixtures = parse_fixtures(args.fixtures)

    missing = helper.get_missing_fixtures(
        planned_only=args.planned,
        priority=args.priority,
        year=args.year,
        specific_fixtures=specific_fixtures
    )

    # Process fixtures
    helper.process_batch(missing, batch_size=args.batch_size)

    # Print summary
    helper.print_summary()

    # Auto-validate if requested
    if args.auto_validate and helper.stats["saved"] > 0:
        print("🚀 Running validation (process_fixtures.py)...")
        print()
        try:
            result = subprocess.run(
                [sys.executable, "scripts/process_fixtures.py", "--planned"],
                check=False
            )
            if result.returncode == 0:
                print("\n✅ Validation complete!")
            else:
                print("\n⚠️  Validation encountered issues (see output above)")
        except Exception as e:
            print(f"\n❌ Failed to run validation: {e}")
            print("   You can run it manually: python scripts/process_fixtures.py --planned")


if __name__ == "__main__":
    main()
