#!/usr/bin/env python
"""
Wisconsin WIAA Coverage Dashboard

Shows current fixture coverage statistics and identifies gaps. Provides
a visual representation of which fixtures are present, planned, or future.

Usage:
    # Show coverage dashboard
    python scripts/show_wiaa_coverage.py

    # Show detailed grid view
    python scripts/show_wiaa_coverage.py --grid

    # Show only missing fixtures
    python scripts/show_wiaa_coverage.py --missing-only

    # Export to JSON
    python scripts/show_wiaa_coverage.py --export coverage.json

Benefits:
    - Quick overview of coverage progress
    - Visual grid shows gaps at a glance
    - Identifies next priorities
    - Tracks progress toward 100% coverage
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

# Paths
FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"


class CoverageDashboard:
    """
    Analyzes and displays Wisconsin WIAA fixture coverage.

    Reads the manifest to determine which fixtures are present, planned,
    or future, and provides visual reporting on coverage progress.
    """

    def __init__(self):
        """Initialize dashboard by loading manifest."""
        self.manifest = self._load_manifest()
        self.stats = self._calculate_stats()

    def _load_manifest(self) -> dict:
        """Load the fixture manifest from YAML file."""
        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"Manifest not found: {MANIFEST_PATH}\n"
                "Make sure you're running this script from the repository root."
            )

        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _calculate_stats(self) -> Dict[str, any]:
        """Calculate coverage statistics from manifest."""
        fixtures = self.manifest.get("fixtures", [])

        # Count by status
        status_counts = defaultdict(int)
        for fix in fixtures:
            status_counts[fix.get("status", "unknown")] += 1

        # Count by priority (for planned fixtures)
        priority_counts = defaultdict(int)
        for fix in fixtures:
            if fix.get("status") == "planned":
                pri = fix.get("priority", "none")
                priority_counts[pri] += 1

        # Count by year
        year_coverage = defaultdict(lambda: {"present": 0, "planned": 0, "future": 0, "total": 0})
        for fix in fixtures:
            year = fix["year"]
            status = fix.get("status", "unknown")
            year_coverage[year][status] += 1
            year_coverage[year]["total"] += 1

        # Count by gender
        gender_coverage = defaultdict(lambda: {"present": 0, "planned": 0, "future": 0, "total": 0})
        for fix in fixtures:
            gender = fix["gender"]
            status = fix.get("status", "unknown")
            gender_coverage[gender][status] += 1
            gender_coverage[gender]["total"] += 1

        # Total possible fixtures
        years = self.manifest.get("years", [])
        genders = self.manifest.get("genders", [])
        divisions = self.manifest.get("divisions", [])
        total_possible = len(years) * len(genders) * len(divisions)

        return {
            "total_possible": total_possible,
            "status_counts": dict(status_counts),
            "priority_counts": dict(priority_counts),
            "year_coverage": dict(year_coverage),
            "gender_coverage": dict(gender_coverage),
            "total_fixtures": len(fixtures)
        }

    def print_summary(self):
        """Print high-level coverage summary."""
        stats = self.stats
        total = stats["total_possible"]
        present = stats["status_counts"].get("present", 0)
        planned = stats["status_counts"].get("planned", 0)
        future = stats["status_counts"].get("future", 0)

        print("\n" + "="*80)
        print("WISCONSIN WIAA FIXTURE COVERAGE DASHBOARD")
        print("="*80)
        print()

        # Overall progress
        pct_present = (present / total * 100) if total > 0 else 0
        pct_planned = (planned / total * 100) if total > 0 else 0
        print(f"Overall Progress: {present}/{total} fixtures ({pct_present:.1f}%)")
        print(self._progress_bar(present, total, width=50))
        print()

        # Breakdown by status
        print("Status Breakdown:")
        print(f"  ✅ Present:  {present:3d} ({pct_present:.1f}%)")
        print(f"  📋 Planned:  {planned:3d} ({pct_planned:.1f}%)")
        print(f"  📅 Future:   {future:3d} ({(future/total*100):.1f}%)")
        print()

        # Priority breakdown (for planned fixtures)
        if planned > 0:
            pri_counts = stats["priority_counts"]
            print("Planned Fixtures by Priority:")
            for pri in sorted(pri_counts.keys()):
                count = pri_counts[pri]
                print(f"  Priority {pri}: {count} fixture(s)")
            print()

        # Coverage by year
        print("Coverage by Year:")
        year_cov = stats["year_coverage"]
        for year in sorted(year_cov.keys()):
            data = year_cov[year]
            present_yr = data["present"]
            total_yr = data["total"]
            pct = (present_yr / total_yr * 100) if total_yr > 0 else 0
            bar = self._progress_bar(present_yr, total_yr, width=20)
            print(f"  {year}: {bar} {present_yr}/{total_yr} ({pct:.0f}%)")
        print()

        # Coverage by gender
        print("Coverage by Gender:")
        gender_cov = stats["gender_coverage"]
        for gender in sorted(gender_cov.keys()):
            data = gender_cov[gender]
            present_gen = data["present"]
            total_gen = data["total"]
            pct = (present_gen / total_gen * 100) if total_gen > 0 else 0
            bar = self._progress_bar(present_gen, total_gen, width=30)
            print(f"  {gender:5s}: {bar} {present_gen}/{total_gen} ({pct:.0f}%)")
        print()

        # Next steps
        if present < total:
            print("Next Steps:")
            if planned > 0:
                pri1 = pri_counts.get(1, 0)
                if pri1 > 0:
                    print(f"  1. Download Priority 1 fixtures ({pri1} remaining)")
                    print(f"     Run: python scripts/open_missing_wiaa_fixtures.py --priority 1")
                else:
                    pri2 = pri_counts.get(2, 0)
                    if pri2 > 0:
                        print(f"  1. Download Priority 2 fixtures ({pri2} remaining)")
                        print(f"     Run: python scripts/open_missing_wiaa_fixtures.py --priority 2")
            elif future > 0:
                print(f"  1. Promote {future} future fixtures to 'planned' status")
                print(f"     Edit manifest_wisconsin.yml to change status: future → planned")
        else:
            print("🎉 Congratulations! 100% coverage achieved!")

        print()

    def print_grid(self):
        """Print detailed coverage grid."""
        years = sorted(self.manifest.get("years", []))
        genders = sorted(self.manifest.get("genders", []))
        divisions = sorted(self.manifest.get("divisions", []))

        # Build lookup dict
        fixtures_dict = {}
        for fix in self.manifest.get("fixtures", []):
            key = (fix["year"], fix["gender"], fix["division"])
            fixtures_dict[key] = fix

        print("\n" + "="*80)
        print("DETAILED COVERAGE GRID")
        print("="*80)
        print()
        print("Legend: ✅ Present  📋 Planned  📅 Future  ❌ Missing")
        print()

        # Print grid by year
        for year in years:
            print(f"\n{year}:")
            print(f"  {'Division':<10}", end="")
            for gender in genders:
                print(f"{gender:<10}", end="")
            print()
            print("  " + "-"*60)

            for div in divisions:
                print(f"  {div:<10}", end="")
                for gender in genders:
                    key = (year, gender, div)
                    if key in fixtures_dict:
                        status = fixtures_dict[key].get("status", "unknown")
                        if status == "present":
                            symbol = "✅"
                        elif status == "planned":
                            pri = fixtures_dict[key].get("priority", "")
                            symbol = f"📋{pri}" if pri else "📋"
                        elif status == "future":
                            symbol = "📅"
                        else:
                            symbol = "❓"
                    else:
                        symbol = "❌"
                    print(f"{symbol:<10}", end="")
                print()

        print()

    def print_missing_only(self):
        """Print only fixtures that are not yet present."""
        print("\n" + "="*80)
        print("MISSING FIXTURES (Not Yet Present)")
        print("="*80)
        print()

        planned = []
        future = []

        for fix in self.manifest.get("fixtures", []):
            status = fix.get("status", "")
            if status == "planned":
                planned.append(fix)
            elif status == "future":
                future.append(fix)

        if planned:
            print(f"📋 PLANNED ({len(planned)} fixtures):")
            print()
            # Group by priority
            by_priority = defaultdict(list)
            for fix in planned:
                pri = fix.get("priority", "none")
                by_priority[pri].append(fix)

            for pri in sorted(by_priority.keys()):
                fixtures_list = by_priority[pri]
                print(f"  Priority {pri} ({len(fixtures_list)} fixtures):")
                for fix in sorted(fixtures_list, key=lambda x: (x["year"], x["gender"], x["division"])):
                    filename = f"{fix['year']}_Basketball_{fix['gender']}_{fix['division']}.html"
                    print(f"    - {fix['year']} {fix['gender']} {fix['division']}: {filename}")
                print()

        if future:
            print(f"📅 FUTURE ({len(future)} fixtures):")
            print(f"   (Mark as 'planned' to include in download workflow)")
            print()

        if not planned and not future:
            print("🎉 No missing fixtures! Coverage is complete.")

        print()

    def export_json(self, output_path: str):
        """Export coverage data to JSON file."""
        data = {
            "summary": self.stats,
            "fixtures": self.manifest.get("fixtures", []),
            "years": self.manifest.get("years", []),
            "genders": self.manifest.get("genders", []),
            "divisions": self.manifest.get("divisions", [])
        }

        output = Path(output_path)
        with output.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"\n✅ Coverage data exported to: {output}")
        print()

    def _progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """Generate a text progress bar."""
        if total == 0:
            return "[" + " "*width + "]"

        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"


def main():
    parser = argparse.ArgumentParser(
        description="Wisconsin WIAA Coverage Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show coverage summary
  python scripts/show_wiaa_coverage.py

  # Show detailed grid view
  python scripts/show_wiaa_coverage.py --grid

  # Show only missing fixtures
  python scripts/show_wiaa_coverage.py --missing-only

  # Export coverage data to JSON
  python scripts/show_wiaa_coverage.py --export coverage.json

  # Combine views
  python scripts/show_wiaa_coverage.py --grid --missing-only
        """
    )

    parser.add_argument(
        "--grid",
        action="store_true",
        help="Show detailed coverage grid"
    )
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Show only fixtures that are not yet present"
    )
    parser.add_argument(
        "--export",
        type=str,
        metavar="PATH",
        help="Export coverage data to JSON file"
    )

    args = parser.parse_args()

    # Initialize dashboard
    try:
        dashboard = CoverageDashboard()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Show requested views
    if not any([args.grid, args.missing_only, args.export]):
        # Default: show summary
        dashboard.print_summary()
    else:
        # Show summary first if multiple views requested
        if args.grid or args.missing_only:
            dashboard.print_summary()

        if args.grid:
            dashboard.print_grid()

        if args.missing_only:
            dashboard.print_missing_only()

        if args.export:
            dashboard.export_json(args.export)


if __name__ == "__main__":
    main()
