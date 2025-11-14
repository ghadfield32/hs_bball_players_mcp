#!/usr/bin/env python
"""
Wisconsin WIAA Season Rollover

Automates the annual process of adding a new WIAA season to the manifest
and optionally downloading/validating fixtures. This script turns the
yearly maintenance into a single command.

Usage:
    # Add 2025 season to manifest
    python scripts/rollover_wiaa_season.py 2025

    # Add season and immediately download fixtures
    python scripts/rollover_wiaa_season.py 2025 --download

    # Full workflow: add, download, validate
    python scripts/rollover_wiaa_season.py 2025 --download --validate

    # Interactive mode (prompts for each step)
    python scripts/rollover_wiaa_season.py 2025 --interactive

Workflow:
    1. Checks if season already exists in manifest
    2. Adds new year to manifest 'years' list
    3. Creates 8 new fixture entries (Boys/Girls × Div1-4) with status="planned", priority=1
    4. Shows before/after coverage statistics
    5. Optionally launches browser helper to download fixtures
    6. Optionally runs validation/manifest update
    7. Guides user through git commit

Benefits:
    - One command for annual rollover
    - No manual YAML editing required
    - Automated coverage tracking
    - Optional end-to-end workflow
    - Clear guidance at each step
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict
import yaml

# Paths
FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"


class SeasonRollover:
    """
    Handles adding a new season to the Wisconsin WIAA manifest.

    This class automates the process of:
    - Adding new year to years list
    - Creating fixture entries for all gender/division combinations
    - Updating manifest safely with backups
    - Coordinating with browser helper and validation scripts
    """

    def __init__(self, year: int, interactive: bool = False):
        """
        Initialize season rollover.

        Args:
            year: The new season year to add (e.g., 2025)
            interactive: If True, prompt user before each step
        """
        self.year = year
        self.interactive = interactive
        self.manifest = None
        self.changes_made = False

    def load_manifest(self) -> bool:
        """
        Load the current manifest.

        Returns:
            True if successful, False otherwise
        """
        if not MANIFEST_PATH.exists():
            print(f"❌ Error: Manifest not found at {MANIFEST_PATH}")
            print("   Make sure you're running from the repository root.")
            return False

        try:
            with MANIFEST_PATH.open("r", encoding="utf-8") as f:
                self.manifest = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"❌ Error loading manifest: {e}")
            return False

    def check_season_exists(self) -> bool:
        """
        Check if season already exists in manifest.

        Returns:
            True if season exists, False otherwise
        """
        years = self.manifest.get("years", [])
        return self.year in years

    def add_season_to_manifest(self) -> bool:
        """
        Add new season to manifest.

        Creates:
        - Year entry in years list
        - 8 new fixture entries (2 genders × 4 divisions)

        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"ADDING SEASON {self.year} TO MANIFEST")
        print(f"{'='*80}\n")

        # Add year to years list
        years = self.manifest.get("years", [])
        if self.year not in years:
            years.append(self.year)
            years.sort()
            self.manifest["years"] = years
            print(f"✅ Added {self.year} to years list")
        else:
            print(f"ℹ️  {self.year} already in years list")

        # Get genders and divisions from manifest
        genders = self.manifest.get("genders", ["Boys", "Girls"])
        divisions = self.manifest.get("divisions", ["Div1", "Div2", "Div3", "Div4"])

        # Check which fixtures already exist
        existing_fixtures = set()
        for fix in self.manifest.get("fixtures", []):
            if fix["year"] == self.year:
                existing_fixtures.add((fix["gender"], fix["division"]))

        # Add new fixture entries
        fixtures = self.manifest.get("fixtures", [])
        added_count = 0

        for gender in genders:
            for division in divisions:
                if (gender, division) not in existing_fixtures:
                    # Create new fixture entry
                    new_fixture = {
                        "year": self.year,
                        "gender": gender,
                        "division": division,
                        "status": "planned",
                        "priority": 1,
                        "notes": f"Added by rollover script for {self.year} season"
                    }
                    fixtures.append(new_fixture)
                    added_count += 1
                    print(f"  + Created: {self.year} {gender} {division}")

        if added_count > 0:
            self.manifest["fixtures"] = fixtures
            print(f"\n✅ Added {added_count} new fixture entries")
            self.changes_made = True
        else:
            print(f"\nℹ️  All {self.year} fixtures already exist in manifest")

        return True

    def save_manifest(self) -> bool:
        """
        Save updated manifest to file with backup.

        Returns:
            True if successful, False otherwise
        """
        if not self.changes_made:
            print("\nℹ️  No changes to save")
            return True

        # Create backup
        backup_path = MANIFEST_PATH.with_suffix(".yml.backup")
        try:
            if MANIFEST_PATH.exists():
                MANIFEST_PATH.rename(backup_path)
                print(f"\n📄 Created backup: {backup_path.name}")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False

        # Save manifest
        try:
            with MANIFEST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    self.manifest,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            print(f"✅ Saved manifest: {MANIFEST_PATH}")
            return True
        except Exception as e:
            # Restore backup on error
            if backup_path.exists():
                backup_path.rename(MANIFEST_PATH)
            print(f"❌ Error saving manifest: {e}")
            print(f"   Restored from backup")
            return False

    def show_coverage_before_after(self):
        """Show coverage statistics before and after changes."""
        print(f"\n{'='*80}")
        print("COVERAGE IMPACT")
        print(f"{'='*80}\n")

        # Run coverage script
        try:
            result = subprocess.run(
                [sys.executable, "scripts/show_wiaa_coverage.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("⚠️  Could not generate coverage report")
        except Exception as e:
            print(f"⚠️  Coverage report error: {e}")

    def launch_browser_helper(self) -> bool:
        """
        Launch browser helper to download new season fixtures.

        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"DOWNLOADING {self.year} FIXTURES")
        print(f"{'='*80}\n")

        print(f"Launching browser helper for {self.year} fixtures...")
        print(f"You'll need to save 8 HTML files (Boys/Girls × Div1-4)")
        print()

        if self.interactive:
            response = input("Continue with download? (Y/n): ").strip().lower()
            if response == 'n':
                print("Skipping download")
                return False

        try:
            # Use --year filter to download only this year's fixtures
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/open_missing_wiaa_fixtures.py",
                    "--year", str(self.year),
                    "--auto-validate"
                ],
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Error launching browser helper: {e}")
            return False

    def guide_commit(self):
        """Guide user through git commit."""
        print(f"\n{'='*80}")
        print("GIT COMMIT")
        print(f"{'='*80}\n")

        print("Suggested git workflow:")
        print()
        print(f"  # Review changes")
        print(f"  git status")
        print(f"  git diff {MANIFEST_PATH}")
        print()
        print(f"  # Stage changes")
        print(f"  git add tests/fixtures/wiaa/")
        print()
        print(f"  # Commit")
        print(f'  git commit -m "Add Wisconsin WIAA {self.year} season to manifest"')
        print()
        print(f"  # Push")
        print(f"  git push")
        print()

        if self.interactive:
            response = input("Run git commands now? (y/N): ").strip().lower()
            if response == 'y':
                self._run_git_workflow()

    def _run_git_workflow(self):
        """Execute git add/commit/push workflow."""
        try:
            # Git status
            print("\n📋 Git status:")
            subprocess.run(["git", "status", "--short"], check=False)

            # Git add
            print("\n➕ Staging changes...")
            subprocess.run(
                ["git", "add", str(FIXTURES_DIR)],
                check=True
            )

            # Git commit
            commit_msg = f"Add Wisconsin WIAA {self.year} season\n\nAdded {self.year} to manifest with 8 planned fixtures (Boys/Girls × Div1-4)"
            print(f"\n💾 Committing...")
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True
            )

            # Ask about push
            response = input("\n🚀 Push to remote? (y/N): ").strip().lower()
            if response == 'y':
                subprocess.run(["git", "push"], check=False)
                print("✅ Pushed to remote")
            else:
                print("⏭️  Skipped push (you can push manually later)")

        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

    def run(self, download: bool = False, validate: bool = False) -> int:
        """
        Execute the season rollover workflow.

        Args:
            download: If True, launch browser helper after adding season
            validate: If True, run validation (implies download)

        Returns:
            0 if successful, non-zero otherwise
        """
        # Validate requires download
        if validate:
            download = True

        # Step 1: Load manifest
        if not self.load_manifest():
            return 1

        # Step 2: Check if season already exists
        if self.check_season_exists():
            print(f"\n✅ Season {self.year} already exists in manifest")
            fixtures = [f for f in self.manifest.get("fixtures", []) if f["year"] == self.year]
            print(f"   Found {len(fixtures)} fixture entries for {self.year}")
            print()

            if not download:
                print("Use --download to download fixtures for this season")
                print(f"  python scripts/rollover_wiaa_season.py {self.year} --download")
                return 0
        else:
            # Step 3: Add season to manifest
            if not self.add_season_to_manifest():
                return 1

            # Step 4: Save manifest
            if not self.save_manifest():
                return 1

        # Step 5: Show coverage
        self.show_coverage_before_after()

        # Step 6: Download fixtures (optional)
        if download:
            if self.interactive:
                print("\nReady to download fixtures for {self.year}")
                print("The browser helper will:")
                print("  1. Open each WIAA URL in your browser")
                print("  2. Guide you to save the HTML file")
                print("  3. Validate and update manifest when done")
                print()

            success = self.launch_browser_helper()
            if not success:
                print("\n⚠️  Download/validation incomplete")
                print(f"   You can run it manually:")
                print(f"   python scripts/open_missing_wiaa_fixtures.py --year {self.year} --auto-validate")

        # Step 7: Guide commit
        if self.changes_made:
            self.guide_commit()

        print(f"\n🎉 Season rollover complete!")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Wisconsin WIAA Season Rollover",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add 2025 season to manifest
  python scripts/rollover_wiaa_season.py 2025

  # Add and download immediately
  python scripts/rollover_wiaa_season.py 2025 --download

  # Full workflow (add, download, validate, commit)
  python scripts/rollover_wiaa_season.py 2025 --download --interactive

  # Non-interactive batch mode
  python scripts/rollover_wiaa_season.py 2025 --download --validate

Notes:
  - Creates 8 new fixtures (Boys/Girls × Div1-4) with status="planned", priority=1
  - Uses safe YAML update with automatic backup
  - Can chain with browser helper and validation scripts
  - Interactive mode guides you through each step
        """
    )

    parser.add_argument(
        "year",
        type=int,
        help="Season year to add (e.g., 2025)"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Launch browser helper to download fixtures after adding season"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after downloading (implies --download)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode (prompts before each step)"
    )

    args = parser.parse_args()

    # Validate year
    if args.year < 2000 or args.year > 2100:
        print(f"❌ Error: Invalid year {args.year}")
        print("   Year must be between 2000 and 2100")
        return 1

    # Run rollover
    rollover = SeasonRollover(args.year, interactive=args.interactive)
    return rollover.run(download=args.download, validate=args.validate)


if __name__ == "__main__":
    sys.exit(main())
