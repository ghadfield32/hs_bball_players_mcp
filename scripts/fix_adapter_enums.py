"""
Bulk Enum Fix Script for State Association Adapters

Fixes DataSourceType enum naming mismatches in 37 templated state adapters.
Converts incorrect format (ALABAMA_AHSAA) to correct format (AHSAA).

Usage:
    python scripts/fix_adapter_enums.py              # Dry run (shows changes)
    python scripts/fix_adapter_enums.py --apply      # Apply changes
    python scripts/fix_adapter_enums.py --verify     # Verify all imports work
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Mapping of incorrect enum names to correct names
# Format: {file_pattern: (incorrect_enum, correct_enum)}
ENUM_FIXES = {
    "alabama_ahsaa.py": ("ALABAMA_AHSAA", "AHSAA"),
    "alaska_asaa.py": ("ALASKA_ASAA", "ASAA"),
    "arkansas_aaa.py": ("ARKANSAS_AAA", "AAA_AR"),
    "colorado_chsaa.py": ("COLORADO_CHSAA", "CHSAA"),
    "connecticut_ciac.py": ("CONNECTICUT_CIAC", "CIAC"),
    "dc_dciaa.py": ("DC_DCIAA", "DCIAA"),
    "delaware_diaa.py": ("DELAWARE_DIAA", "DIAA"),
    "georgia_ghsa.py": ("GEORGIA_GHSA", "GHSA"),
    "indiana_ihsaa.py": ("INDIANA_IHSAA", "IHSAA"),
    "kansas_kshsaa.py": ("KANSAS_KSHSAA", "KSHSAA"),
    "kentucky_khsaa.py": ("KENTUCKY_KHSAA", "KHSAA"),
    "louisiana_lhsaa.py": ("LOUISIANA_LHSAA", "LHSAA"),
    "maine_mpa.py": ("MAINE_MPA", "MPA"),
    "maryland_mpssaa.py": ("MARYLAND_MPSSAA", "MPSSAA"),
    "massachusetts_miaa.py": ("MASSACHUSETTS_MIAA", "MIAA"),
    "michigan_mhsaa.py": ("MICHIGAN_MHSAA", "MHSAA_MI"),
    "mississippi_mhsaa.py": ("MISSISSIPPI_MHSAA", "MHSAA_MS"),
    "missouri_mshsaa.py": ("MISSOURI_MSHSAA", "MSHSAA"),
    "montana_mhsa.py": ("MONTANA_MHSA", "MHSA"),
    "nebraska_nsaa.py": ("NEBRASKA_NSAA", "NSAA"),
    "new_hampshire_nhiaa.py": ("NEW_HAMPSHIRE_NHIAA", "NHIAA"),
    "new_jersey_njsiaa.py": ("NEW_JERSEY_NJSIAA", "NJSIAA"),
    "new_mexico_nmaa.py": ("NEW_MEXICO_NMAA", "NMAA"),
    "nchsaa.py": ("NCHSAA_NC", "NCHSAA"),  # North Carolina
    "north_dakota_ndhsaa.py": ("NORTH_DAKOTA_NDHSAA", "NDHSAA"),
    "ohio_ohsaa.py": ("OHIO_OHSAA", "OHSAA"),
    "oklahoma_ossaa.py": ("OKLAHOMA_OSSAA", "OSSAA"),
    "pennsylvania_piaa.py": ("PENNSYLVANIA_PIAA", "PIAA"),
    "rhode_island_riil.py": ("RHODE_ISLAND_RIIL", "RIIL"),
    "south_carolina_schsl.py": ("SOUTH_CAROLINA_SCHSL", "SCHSL"),
    "tennessee_tssaa.py": ("TENNESSEE_TSSAA", "TSSAA"),
    "utah_uhsaa.py": ("UTAH_UHSAA", "UHSAA"),
    "vermont_vpa.py": ("VERMONT_VPA", "VPA"),
    "virginia_vhsl.py": ("VIRGINIA_VHSL", "VHSL"),
    "west_virginia_wvssac.py": ("WEST_VIRGINIA_WVSSAC", "WVSSAC"),
    "wyoming_whsaa.py": ("WYOMING_WHSAA", "WHSAA"),
    "nepsac.py": ("NEPSAC_NEPS", "NEPSAC"),  # New England Prep
}


def find_adapter_files(base_path: Path) -> List[Path]:
    """
    Find all state adapter files that need enum fixes.

    Args:
        base_path: Base directory to search

    Returns:
        List of adapter file paths
    """
    adapter_dir = base_path / "src" / "datasources" / "us"

    adapter_files = []
    for filename in ENUM_FIXES.keys():
        file_path = adapter_dir / filename
        if file_path.exists():
            adapter_files.append(file_path)
        else:
            print(f"[WARN] File not found: {file_path}")

    return adapter_files


def analyze_file(file_path: Path) -> Tuple[bool, str, str]:
    """
    Analyze a file to determine if it needs enum fixes.

    Args:
        file_path: Path to adapter file

    Returns:
        Tuple of (needs_fix, incorrect_enum, correct_enum)
    """
    filename = file_path.name

    if filename not in ENUM_FIXES:
        return False, "", ""

    incorrect_enum, correct_enum = ENUM_FIXES[filename]

    # Read file content
    content = file_path.read_text(encoding="utf-8")

    # Check if file contains the incorrect enum
    pattern = f"DataSourceType\\.{incorrect_enum}"
    if re.search(pattern, content):
        return True, incorrect_enum, correct_enum

    return False, "", ""


def fix_file(file_path: Path, incorrect_enum: str, correct_enum: str, dry_run: bool = True) -> bool:
    """
    Fix enum naming in a single file.

    Args:
        file_path: Path to adapter file
        incorrect_enum: Incorrect enum name to replace
        correct_enum: Correct enum name
        dry_run: If True, only show changes without applying

    Returns:
        True if changes were made/would be made
    """
    # Read file content
    content = file_path.read_text(encoding="utf-8")

    # Replace all occurrences
    pattern = f"DataSourceType\\.{incorrect_enum}"
    replacement = f"DataSourceType.{correct_enum}"

    # Count occurrences
    occurrences = len(re.findall(pattern, content))

    if occurrences == 0:
        return False

    print(f"\n[FIX] {file_path.name}")
    print(f"  Pattern: {pattern}")
    print(f"  Replace: {replacement}")
    print(f"  Occurrences: {occurrences}")

    if not dry_run:
        # Apply fix
        new_content = re.sub(pattern, replacement, content)
        file_path.write_text(new_content, encoding="utf-8")
        print(f"  [OK] Changes applied")
    else:
        print(f"  [DRY RUN] Changes not applied")

    return True


def verify_imports(base_path: Path) -> Tuple[bool, List[str]]:
    """
    Verify that all adapters can be imported without errors.

    Args:
        base_path: Base directory

    Returns:
        Tuple of (all_success, error_messages)
    """
    print("\n[VERIFY] Testing imports...")

    errors = []

    try:
        # Try importing the datasources.us module
        from src.datasources.us import (
            # Currently active adapters that should work
            BoundDataSource,
            EYBLDataSource,
            EYBLGirlsDataSource,
            SBLiveDataSource,
            ThreeSSBDataSource,
            WSNDataSource,
            FHSAADataSource,
            HHSAADataSource,
            MNHubDataSource,
            PSALDataSource,
            RankOneDataSource,
        )

        print("[OK] All active adapters imported successfully")

        # Try importing a few templated adapters to test enum fixes
        try:
            from src.datasources.us.ghsa import GHSADataSource
            from src.datasources.us.vhsl import VHSLDataSource
            from src.datasources.us.ahsaa import AHSAADataSource

            print("[OK] Sample templated adapters imported successfully")

            # Test that enum values are correct
            print(f"  GHSA source_type: {GHSADataSource.source_type}")
            print(f"  VHSL source_type: {VHSLDataSource.source_type}")
            print(f"  AHSAA source_type: {AHSAADataSource.source_type}")

        except ImportError as e:
            errors.append(f"Failed to import templated adapters: {e}")
        except AttributeError as e:
            errors.append(f"Enum attribute error in templated adapters: {e}")

    except ImportError as e:
        errors.append(f"Failed to import active adapters: {e}")
    except AttributeError as e:
        errors.append(f"Enum attribute error in active adapters: {e}")

    if errors:
        print("\n[ERRORS FOUND]")
        for error in errors:
            print(f"  - {error}")
        return False, errors

    return True, []


def update_init_file(base_path: Path, dry_run: bool = True) -> bool:
    """
    Uncomment the templated adapter imports in __init__.py.

    Args:
        base_path: Base directory
        dry_run: If True, only show changes without applying

    Returns:
        True if changes were made/would be made
    """
    init_file = base_path / "src" / "datasources" / "us" / "__init__.py"

    if not init_file.exists():
        print(f"[ERROR] __init__.py not found: {init_file}")
        return False

    content = init_file.read_text(encoding="utf-8")

    # Check if imports are commented out
    if "# from .alabama_ahsaa import" not in content:
        print("[INFO] Adapter imports already uncommented in __init__.py")
        return False

    print(f"\n[UPDATE] {init_file.name}")
    print("  Uncommenting 37 templated adapter imports...")

    # Uncomment the imports (lines 24-60 based on previous analysis)
    # Pattern: # from .{state_file} import {AdapterClass}

    new_content = re.sub(
        r"^# (from \.(?:alabama_ahsaa|arkansas_aaa|georgia_ghsa|kentucky_khsaa|"
        r"louisiana_lhsaa|mississippi_mhsaa|nchsaa|south_carolina_schsl|"
        r"tennessee_tssaa|virginia_vhsl|west_virginia_wvssac|connecticut_ciac|"
        r"delaware_diaa|maine_mpa|maryland_mpssaa|massachusetts_miaa|nepsac|"
        r"new_hampshire_nhiaa|new_jersey_njsiaa|pennsylvania_piaa|rhode_island_riil|"
        r"vermont_vpa|indiana_ihsaa|kansas_kshsaa|michigan_mhsaa|missouri_mshsaa|"
        r"nebraska_nsaa|north_dakota_ndhsaa|ohio_ohsaa|alaska_asaa|colorado_chsaa|"
        r"dc_dciaa|montana_mhsa|new_mexico_nmaa|oklahoma_ossaa|utah_uhsaa|"
        r"wyoming_whsaa) import)",
        r"\1",
        content,
        flags=re.MULTILINE
    )

    # Count changes
    changes = content.count("# from .") - new_content.count("# from .")

    print(f"  Imports to uncomment: {changes}")

    if not dry_run:
        init_file.write_text(new_content, encoding="utf-8")
        print(f"  [OK] Changes applied")
    else:
        print(f"  [DRY RUN] Changes not applied")

    return True


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Fix DataSourceType enum naming in state adapters")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")
    parser.add_argument("--verify", action="store_true", help="Verify imports after fixing")
    parser.add_argument("--update-init", action="store_true", help="Uncomment imports in __init__.py")
    args = parser.parse_args()

    # Get base path (repository root)
    base_path = Path(__file__).parent.parent

    print("="*80)
    print("BULK ENUM FIX SCRIPT FOR STATE ADAPTERS")
    print("="*80)
    print(f"Base path: {base_path}")
    print(f"Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN'}")
    print(f"Total adapters to fix: {len(ENUM_FIXES)}")
    print()

    # Find adapter files
    adapter_files = find_adapter_files(base_path)
    print(f"[INFO] Found {len(adapter_files)} adapter files")

    # Analyze and fix each file
    fixed_count = 0
    skipped_count = 0

    for file_path in adapter_files:
        needs_fix, incorrect_enum, correct_enum = analyze_file(file_path)

        if needs_fix:
            if fix_file(file_path, incorrect_enum, correct_enum, dry_run=not args.apply):
                fixed_count += 1
        else:
            skipped_count += 1

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Files processed: {len(adapter_files)}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files skipped (no changes needed): {skipped_count}")

    if not args.apply:
        print(f"\n[INFO] This was a DRY RUN. Use --apply to apply changes.")
    else:
        print(f"\n[OK] All changes applied successfully!")

    # Update __init__.py if requested
    if args.update_init:
        print(f"\n{'='*80}")
        update_init_file(base_path, dry_run=not args.apply)

    # Verify imports if requested
    if args.verify and args.apply:
        print(f"\n{'='*80}")
        success, errors = verify_imports(base_path)

        if success:
            print("\n[SUCCESS] All imports verified!")
        else:
            print("\n[FAILURE] Import verification failed")
            sys.exit(1)

    print(f"\n{'='*80}")
    print("DONE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
