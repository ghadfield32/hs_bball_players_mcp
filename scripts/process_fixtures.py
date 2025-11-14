#!/usr/bin/env python
"""
Wisconsin WIAA Fixture Batch Processor

Automates the fixture validation → testing → manifest update workflow for
multiple fixtures at once. This script significantly speeds up the process
of adding new fixtures to the test suite.

Usage:
    # Process all planned fixtures that have HTML files
    python scripts/process_fixtures.py

    # Process specific fixtures
    python scripts/process_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"

    # Dry run (validate only, don't update manifest)
    python scripts/process_fixtures.py --dry-run

    # Process and auto-commit
    python scripts/process_fixtures.py --commit

Workflow:
    1. Reads manifest to identify target fixtures
    2. Checks which fixture HTML files exist locally
    3. Runs inspection script (validate parsing, data quality)
    4. If validation passes, updates manifest status: planned → present
    5. Runs targeted pytest to confirm fixture works in tests
    6. Generates summary report

Benefits:
    - Process multiple fixtures in one command
    - Automatic manifest updates (no manual YAML editing)
    - Clear reporting of success/failures/missing files
    - Optional git integration
    - Safe: validates before updating, backs up manifest
"""

import argparse
import asyncio
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import yaml
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource, DataMode


# Paths
FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"
INSPECT_SCRIPT = Path("scripts/inspect_wiaa_fixture.py")


class FixtureProcessor:
    """Batch processor for Wisconsin WIAA fixtures."""

    def __init__(self, dry_run: bool = False, verbose: bool = True):
        self.dry_run = dry_run
        self.verbose = verbose
        self.manifest = self._load_manifest()
        self.results = defaultdict(list)

    def _load_manifest(self) -> dict:
        """Load the fixture manifest."""
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _save_manifest(self) -> None:
        """Save the updated manifest."""
        if self.dry_run:
            print("  [DRY RUN] Would update manifest (not actually saving)")
            return

        # Backup existing manifest
        backup_path = MANIFEST_PATH.with_suffix(".yml.backup")
        MANIFEST_PATH.rename(backup_path)
        print(f"  📄 Backed up manifest to {backup_path.name}")

        try:
            with MANIFEST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(self.manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"  ✅ Manifest updated: {MANIFEST_PATH}")
        except Exception as e:
            # Restore backup on error
            backup_path.rename(MANIFEST_PATH)
            raise Exception(f"Failed to save manifest, restored from backup: {e}")

    def _get_fixture_path(self, year: int, gender: str, division: str) -> Path:
        """Get the expected fixture file path."""
        return FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"

    def _get_fixture_entry(self, year: int, gender: str, division: str) -> Optional[dict]:
        """Find fixture entry in manifest."""
        for entry in self.manifest.get("fixtures", []):
            if (entry["year"] == year and
                entry["gender"] == gender and
                entry["division"] == division):
                return entry
        return None

    def _update_fixture_status(self, year: int, gender: str, division: str, status: str, notes: str = None) -> None:
        """Update fixture status in manifest."""
        entry = self._get_fixture_entry(year, gender, division)
        if entry:
            entry["status"] = status
            if notes:
                entry["notes"] = notes
        else:
            print(f"  ⚠️  Warning: No manifest entry found for {year} {gender} {division}")

    def _run_inspection(self, year: int, gender: str, division: str) -> Tuple[bool, str]:
        """
        Run fixture inspection script.

        Returns:
            (success: bool, message: str)
        """
        try:
            result = subprocess.run(
                [sys.executable, str(INSPECT_SCRIPT),
                 "--year", str(year),
                 "--gender", gender,
                 "--division", division,
                 "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "All checks passed"
            else:
                # Extract error message from output
                error_lines = result.stdout.split("\n") if result.stdout else result.stderr.split("\n")
                error_msg = next((line for line in error_lines if "FAIL" in line or "Error" in line), "Validation failed")
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "Inspection timed out (>30s)"
        except Exception as e:
            return False, f"Inspection error: {str(e)}"

    def _run_tests(self, year: int, gender: str, division: str) -> Tuple[bool, str]:
        """
        Run pytest for specific fixture.

        Returns:
            (success: bool, message: str)
        """
        try:
            test_key = f"{year}_{gender}_{division}"
            result = subprocess.run(
                [sys.executable, "-m", "pytest",
                 "tests/test_datasources/test_wisconsin_wiaa_historical.py",
                 "-k", test_key,
                 "-v", "--tb=line"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Count passed tests
                passed_count = result.stdout.count(" PASSED")
                return True, f"{passed_count} tests passed"
            else:
                # Extract failure info
                if "FAILED" in result.stdout:
                    return False, "Some tests failed (see pytest output)"
                else:
                    return False, "Tests did not pass"

        except subprocess.TimeoutExpired:
            return False, "Tests timed out (>60s)"
        except Exception as e:
            return False, f"Test error: {str(e)}"

    def process_fixture(self, year: int, gender: str, division: str) -> Dict[str, any]:
        """
        Process a single fixture through the validation pipeline.

        Returns:
            Dict with processing results
        """
        fixture_id = f"{year} {gender} {division}"
        print(f"\n{'='*80}")
        print(f"Processing: {fixture_id}")
        print(f"{'='*80}")

        result = {
            "year": year,
            "gender": gender,
            "division": division,
            "fixture_id": fixture_id,
            "file_exists": False,
            "manifest_entry_exists": False,
            "original_status": None,
            "inspection_passed": False,
            "inspection_message": "",
            "tests_passed": False,
            "test_message": "",
            "manifest_updated": False,
            "new_status": None
        }

        # Check 1: Fixture file exists
        fixture_path = self._get_fixture_path(year, gender, division)
        result["file_exists"] = fixture_path.exists()

        if not result["file_exists"]:
            print(f"  ❌ Fixture file not found: {fixture_path.name}")
            print(f"     Action: Download from WIAA website and place in {FIXTURES_DIR}/")
            result["inspection_message"] = "File not found - needs download"
            return result

        print(f"  ✅ Fixture file exists: {fixture_path.name}")

        # Check 2: Manifest entry exists
        manifest_entry = self._get_fixture_entry(year, gender, division)
        result["manifest_entry_exists"] = manifest_entry is not None

        if not result["manifest_entry_exists"]:
            print(f"  ⚠️  No manifest entry found (unexpected)")
            result["inspection_message"] = "No manifest entry"
            return result

        result["original_status"] = manifest_entry.get("status", "unknown")
        print(f"  📋 Current manifest status: {result['original_status']}")

        # Check 3: Run inspection
        print(f"  🔍 Running inspection script...")
        inspection_passed, inspection_msg = self._run_inspection(year, gender, division)
        result["inspection_passed"] = inspection_passed
        result["inspection_message"] = inspection_msg

        if not inspection_passed:
            print(f"  ❌ Inspection failed: {inspection_msg}")
            print(f"     Action: Fix fixture or parser before marking as present")
            return result

        print(f"  ✅ Inspection passed: {inspection_msg}")

        # Check 4: Run tests
        print(f"  🧪 Running tests...")
        tests_passed, test_msg = self._run_tests(year, gender, division)
        result["tests_passed"] = tests_passed
        result["test_message"] = test_msg

        if not tests_passed:
            print(f"  ❌ Tests failed: {test_msg}")
            print(f"     Action: Review test failures before marking as present")
            return result

        print(f"  ✅ Tests passed: {test_msg}")

        # Check 5: Update manifest if everything passed
        if result["original_status"] != "present":
            print(f"  📝 Updating manifest: {result['original_status']} → present")
            timestamp = datetime.now().strftime("%Y-%m-%d")
            notes = f"Validated {timestamp} - inspection and tests passed"
            self._update_fixture_status(year, gender, division, "present", notes)
            result["manifest_updated"] = True
            result["new_status"] = "present"
        else:
            print(f"  ℹ️  Already marked as present in manifest")
            result["new_status"] = "present"

        print(f"  🎉 SUCCESS: {fixture_id} is ready!")
        return result

    def process_batch(self, fixtures: List[Tuple[int, str, str]]) -> None:
        """
        Process multiple fixtures and generate summary report.

        Args:
            fixtures: List of (year, gender, division) tuples
        """
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING: {len(fixtures)} fixtures")
        print(f"{'='*80}")

        if self.dry_run:
            print("  🏃 DRY RUN MODE: No changes will be saved")

        all_results = []

        for year, gender, division in fixtures:
            result = self.process_fixture(year, gender, division)
            all_results.append(result)

            # Categorize result
            if not result["file_exists"]:
                self.results["needs_download"].append(result)
            elif not result["inspection_passed"]:
                self.results["inspection_failed"].append(result)
            elif not result["tests_passed"]:
                self.results["tests_failed"].append(result)
            elif result["manifest_updated"]:
                self.results["newly_validated"].append(result)
            else:
                self.results["already_present"].append(result)

        # Save manifest if any updates were made
        if self.results["newly_validated"] and not self.dry_run:
            print(f"\n{'='*80}")
            print("SAVING MANIFEST")
            print(f"{'='*80}")
            self._save_manifest()

        # Print summary
        self._print_summary()

    def _print_summary(self) -> None:
        """Print batch processing summary."""
        print(f"\n{'='*80}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*80}\n")

        # Newly validated (success!)
        if self.results["newly_validated"]:
            print(f"✅ NEWLY VALIDATED ({len(self.results['newly_validated'])}):")
            for r in self.results["newly_validated"]:
                print(f"   - {r['fixture_id']}: {r['original_status']} → present")
            print()

        # Already present
        if self.results["already_present"]:
            print(f"ℹ️  ALREADY PRESENT ({len(self.results['already_present'])}):")
            for r in self.results["already_present"]:
                print(f"   - {r['fixture_id']}")
            print()

        # Needs download
        if self.results["needs_download"]:
            print(f"📥 NEEDS DOWNLOAD ({len(self.results['needs_download'])}):")
            for r in self.results["needs_download"]:
                filename = f"{r['year']}_Basketball_{r['gender']}_{r['division']}.html"
                print(f"   - {r['fixture_id']}: {filename}")
            print(f"   Action: Download these from WIAA website and re-run")
            print()

        # Inspection failed
        if self.results["inspection_failed"]:
            print(f"❌ INSPECTION FAILED ({len(self.results['inspection_failed'])}):")
            for r in self.results["inspection_failed"]:
                print(f"   - {r['fixture_id']}: {r['inspection_message']}")
            print(f"   Action: Fix fixtures or parser before marking as present")
            print()

        # Tests failed
        if self.results["tests_failed"]:
            print(f"❌ TESTS FAILED ({len(self.results['tests_failed'])}):")
            for r in self.results["tests_failed"]:
                print(f"   - {r['fixture_id']}: {r['test_message']}")
            print(f"   Action: Review test failures")
            print()

        # Overall stats
        total = sum(len(v) for v in self.results.values())
        success = len(self.results["newly_validated"]) + len(self.results["already_present"])
        print(f"TOTAL PROCESSED: {total}")
        print(f"SUCCESS: {success}/{total} ({success/total*100:.1f}%)")

        # Next steps
        if self.results["newly_validated"]:
            print(f"\n💡 NEXT STEPS:")
            print(f"   1. Review changes to manifest_wisconsin.yml")
            print(f"   2. Run full test suite to confirm: pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v")
            print(f"   3. Commit changes: git add tests/fixtures/wiaa && git commit -m 'Add {len(self.results['newly_validated'])} Wisconsin WIAA fixtures'")


def get_planned_fixtures_from_manifest() -> List[Tuple[int, str, str]]:
    """Get all fixtures marked as 'planned' in manifest."""
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    planned = []
    for entry in manifest.get("fixtures", []):
        if entry.get("status") == "planned":
            planned.append((entry["year"], entry["gender"], entry["division"]))

    return planned


def main():
    parser = argparse.ArgumentParser(
        description="Batch process Wisconsin WIAA fixtures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--fixtures",
        nargs="+",
        help='Specific fixtures to process: "2024,Boys,Div2" "2024,Girls,Div3"'
    )

    parser.add_argument(
        "--planned",
        action="store_true",
        help="Process all fixtures marked as 'planned' in manifest (default if no --fixtures)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, don't update manifest"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    # Determine which fixtures to process
    if args.fixtures:
        # Parse fixture strings
        fixtures = []
        for combo in args.fixtures:
            parts = combo.split(",")
            if len(parts) != 3:
                print(f"❌ Invalid fixture format: {combo}")
                print(f"   Expected: year,gender,division (e.g., '2024,Boys,Div2')")
                sys.exit(1)
            try:
                year = int(parts[0])
                gender = parts[1]
                division = parts[2]
                fixtures.append((year, gender, division))
            except ValueError as e:
                print(f"❌ Error parsing fixture: {combo}: {e}")
                sys.exit(1)
    else:
        # Default: all planned fixtures
        fixtures = get_planned_fixtures_from_manifest()
        if not fixtures:
            print("No 'planned' fixtures found in manifest")
            print(f"Manifest: {MANIFEST_PATH}")
            sys.exit(0)

        print(f"Found {len(fixtures)} planned fixtures in manifest")

    # Process fixtures
    processor = FixtureProcessor(dry_run=args.dry_run, verbose=not args.quiet)
    processor.process_batch(fixtures)

    # Exit code based on results
    if processor.results["inspection_failed"] or processor.results["tests_failed"]:
        sys.exit(1)  # Failures occurred
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
