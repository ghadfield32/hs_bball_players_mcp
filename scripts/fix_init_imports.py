"""
Fix __init__.py Import Names

Updates src/datasources/us/__init__.py to import correct class names
from state association adapters.

Usage:
    python scripts/fix_init_imports.py         # Dry run
    python scripts/fix_init_imports.py --apply # Apply changes
"""

import argparse
import re
from pathlib import Path


# Mapping of: (file_module, incorrect_import_name, correct_class_name)
IMPORT_FIXES = [
    # Southeast
    ("alabama_ahsaa", "AHSAADataSource", "AlabamaAhsaaDataSource"),
    ("arkansas_aaa", "AAADataSource", "ArkansasAaaDataSource"),
    ("georgia_ghsa", "GHSADataSource", "GeorgiaGhsaDataSource"),
    ("kentucky_khsaa", "KHSAADataSource", "KentuckyKhsaaDataSource"),
    ("louisiana_lhsaa", "LHSAADataSource", "LouisianaLhsaaDataSource"),
    ("mississippi_mhsaa", "MHSAAMSDataSource", "MississippiMhsaaDataSource"),
    ("nchsaa", "NCHSAADataSource", "NchsaaDataSource"),
    ("south_carolina_schsl", "SCHSLDataSource", "SouthCarolinaSchslDataSource"),
    ("tennessee_tssaa", "TSSAADataSource", "TennesseeTssaaDataSource"),
    ("virginia_vhsl", "VHSLDataSource", "VirginiaVhslDataSource"),
    ("west_virginia_wvssac", "WVSSACDataSource", "WestVirginiaWvssacDataSource"),
    # Northeast
    ("connecticut_ciac", "CIACDataSource", "ConnecticutCiacDataSource"),
    ("delaware_diaa", "DIAADataSource", "DelawareDiaaDataSource"),
    ("maine_mpa", "MPADataSource", "MaineMpaDataSource"),
    ("maryland_mpssaa", "MPSSAADataSource", "MarylandMpssaaDataSource"),
    ("massachusetts_miaa", "MIAADataSource", "MassachusettsMiaaDataSource"),
    ("nepsac", "NEPSACDataSource", "NepsacDataSource"),
    ("new_hampshire_nhiaa", "NHIAADataSource", "NewHampshireNhiaaDataSource"),
    ("new_jersey_njsiaa", "NJSIAADataSource", "NewJerseyNjsiaaDataSource"),
    ("pennsylvania_piaa", "PIAADataSource", "PennsylvaniaPiaaDataSource"),
    ("rhode_island_riil", "RIILDataSource", "RhodeIslandRiilDataSource"),
    ("vermont_vpa", "VPADataSource", "VermontVpaDataSource"),
    # Midwest
    ("indiana_ihsaa", "IHSAADataSource", "IndianaIhsaaDataSource"),
    ("kansas_kshsaa", "KSHSAADataSource", "KansasKshsaaDataSource"),
    ("michigan_mhsaa", "MHSAAMIDataSource", "MichiganMhsaaDataSource"),
    ("missouri_mshsaa", "MSHSAADataSource", "MissouriMshsaaDataSource"),
    ("nebraska_nsaa", "NSAADataSource", "NebraskaNsaaDataSource"),
    ("north_dakota_ndhsaa", "NDHSAADataSource", "NorthDakotaNdhsaaDataSource"),
    ("ohio_ohsaa", "OHSAADataSource", "OhioOhsaaDataSource"),
    # Southwest/West
    ("alaska_asaa", "ASAADataSource", "AlaskaAsaaDataSource"),
    ("colorado_chsaa", "CHSAADataSource", "ColoradoChsaaDataSource"),
    ("dc_dciaa", "DCIAADataSource", "DcDciaaDataSource"),
    ("montana_mhsa", "MHSADataSource", "MontanaMhsaDataSource"),
    ("new_mexico_nmaa", "NMAADataSource", "NewMexicoNmaaDataSource"),
    ("oklahoma_ossaa", "OSSAADataSource", "OklahomaOssaaDataSource"),
    ("utah_uhsaa", "UHSAADataSource", "UtahUhsaaDataSource"),
    ("wyoming_whsaa", "WHSAADataSource", "WyomingWhsaaDataSource"),
]


def fix_init_file(base_path: Path, dry_run: bool = True) -> bool:
    """
    Fix imports in __init__.py to use correct class names.

    Args:
        base_path: Repository root path
        dry_run: If True, only show changes without applying

    Returns:
        True if changes were made
    """
    init_file = base_path / "src" / "datasources" / "us" / "__init__.py"

    if not init_file.exists():
        print(f"[ERROR] __init__.py not found: {init_file}")
        return False

    print(f"[FIX] {init_file.name}")
    print()

    content = init_file.read_text(encoding="utf-8")
    new_content = content
    changes_made = 0

    for module, incorrect_name, correct_name in IMPORT_FIXES:
        # Pattern: from .{module} import {incorrect_name}
        pattern = f"from \\.{module} import {incorrect_name}"
        replacement = f"from .{module} import {correct_name}"

        if re.search(pattern, new_content):
            print(f"  [{module}]")
            print(f"    OLD: from .{module} import {incorrect_name}")
            print(f"    NEW: from .{module} import {correct_name}")

            new_content = re.sub(pattern, replacement, new_content)
            changes_made += 1

    if changes_made == 0:
        print("  [INFO] No changes needed")
        return False

    print()
    print(f"  Total imports fixed: {changes_made}")

    if not dry_run:
        init_file.write_text(new_content, encoding="utf-8")
        print(f"  [OK] Changes applied")
    else:
        print(f"  [DRY RUN] Changes not applied")

    return True


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="Fix __init__.py import names")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent

    print("="*80)
    print("FIX __init__.py IMPORT NAMES")
    print("="*80)
    print(f"Base path: {base_path}")
    print(f"Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN'}")
    print()

    success = fix_init_file(base_path, dry_run=not args.apply)

    if success:
        print()
        print("="*80)
        if args.apply:
            print("[SUCCESS] Import names fixed!")
        else:
            print("[INFO] This was a DRY RUN. Use --apply to apply changes.")
        print("="*80)
    else:
        print()
        print("="*80)
        print("[INFO] No changes needed or file not found")
        print("="*80)


if __name__ == "__main__":
    main()
