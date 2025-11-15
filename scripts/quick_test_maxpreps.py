"""
Quick MaxPreps Test Script

Simple test to verify MaxPreps adapter works before full validation.
Tests basic functionality without extensive data collection.

**LEGAL WARNING**: Makes real requests to MaxPreps. Use with permission only.

Usage:
    python scripts/quick_test_maxpreps.py

Author: Claude Code
Date: 2025-11-14
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.maxpreps import MaxPrepsDataSource


async def quick_test():
    """Quick test of MaxPreps adapter."""
    print("\n" + "=" * 70)
    print("MaxPreps Quick Test")
    print("=" * 70)
    print("\n⚠️  LEGAL WARNING:")
    print("   This test makes real network requests to MaxPreps.")
    print("   MaxPreps ToS prohibits scraping.")
    print("   Only proceed with explicit permission.\n")

    response = input("Do you have permission to proceed? (yes/no): ")
    if response.lower() != "yes":
        print("\n✋ Test cancelled.")
        return

    try:
        print("\n[1/3] Initializing MaxPreps adapter...")
        async with MaxPrepsDataSource() as maxpreps:
            print(f"      ✓ Adapter initialized")
            print(f"      - States supported: {len(maxpreps.ALL_US_STATES)}")

            print("\n[2/3] Testing state validation...")
            try:
                state = maxpreps._validate_state("CA")
                print(f"      ✓ State 'CA' validated as '{state}'")
            except ValueError as e:
                print(f"      ✗ Validation failed: {e}")
                return

            print("\n[3/3] Testing player search (limit 3)...")
            print("      NOTE: This may take 30-60 seconds...")

            try:
                players = await maxpreps.search_players(state="CA", limit=3)
                print(f"\n      ✓ Found {len(players)} player(s)")

                for idx, player in enumerate(players, 1):
                    print(f"\n      Player {idx}:")
                    print(f"         Name: {player.full_name}")
                    print(f"         School: {player.school_name or 'N/A'}")
                    print(f"         Position: {player.position or 'N/A'}")
                    print(f"         Grad Year: {player.grad_year or 'N/A'}")

                print(f"\n✅ MaxPreps adapter is working!")
                print(f"\nNext steps:")
                print(f"  1. Run full validation: python scripts/validate_maxpreps.py --state CA")
                print(f"  2. Review: docs/MAXPREPS_VALIDATION_GUIDE.md")

            except Exception as e:
                print(f"\n      ✗ Search failed: {e}")
                print(f"\nTroubleshooting:")
                print(f"  - Check internet connection")
                print(f"  - MaxPreps may be blocking automated requests")
                print(f"  - Try different state or increase timeout")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(quick_test())
