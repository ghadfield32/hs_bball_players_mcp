"""
Test Nevada NIAA Fix

Test if browser User-Agent helps Nevada NIAA bypass CloudFront protection.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.nevada_niaa import NevadaNIAADataSource


async def test_nevada():
    """Test Nevada NIAA with browser User-Agent."""
    print("\n" + "="*60)
    print("Testing Nevada NIAA (with browser User-Agent)")
    print("="*60)

    source = NevadaNIAADataSource()
    print(f"Base URL: {source.base_url}")
    print(f"PDF Cache Size: {len(source.pdf_cache)}")

    # Check pdfplumber
    try:
        import pdfplumber
        print(f"pdfplumber: INSTALLED (version: {pdfplumber.__version__})")
    except ImportError:
        print(f"pdfplumber: NOT INSTALLED")

    # Test health check
    print("\n[Health Check]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")

    # Test bracket URL construction
    print("\n[URL Construction]")
    url = source._build_bracket_url("5A", "Boys", 2025)
    print(f"  URL: {url}")

    # Try to fetch a bracket (quick test)
    print("\n[Bracket Fetch Test]")
    print("  Attempting to fetch Boys 5A 2024-25 bracket...")
    try:
        brackets = await source.get_tournament_brackets(
            season="2024-25",
            division="5A",
            gender="Boys"
        )
        print(f"  Result: SUCCESS")
        print(f"  Games: {len(brackets.get('games', []))}")
        print(f"  Teams: {len(brackets.get('teams', []))}")
    except Exception as e:
        print(f"  Result: ERROR - {type(e).__name__}: {str(e)[:200]}")


async def main():
    """Run Nevada NIAA test."""
    await test_nevada()

    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
