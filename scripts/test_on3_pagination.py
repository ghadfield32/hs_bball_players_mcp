"""
Test On3/Rivals Adapter Pagination

Validates multi-page fetching works correctly.

Usage:
    python scripts/test_on3_pagination.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pagination():
    """Test On3 adapter pagination by fetching 150 rankings."""
    from src.datasources.recruiting.on3 import On3DataSource

    logger.info("="*60)
    logger.info("Testing On3/Rivals Pagination")
    logger.info("="*60)
    logger.info("")

    on3 = On3DataSource()

    try:
        # Test 1: Fetch 150 rankings (requires 3 pages)
        logger.info("Test 1: Fetching 150 rankings (should fetch 3 pages)...")
        logger.info("")

        rankings = await on3.get_rankings(class_year=2025, limit=150)

        if not rankings:
            logger.error("FAILED: No rankings returned")
            return False

        logger.info(f"SUCCESS: Fetched {len(rankings)} rankings")
        logger.info("")

        # Validation checks
        logger.info("="*60)
        logger.info("VALIDATION CHECKS")
        logger.info("="*60)
        logger.info("")

        issues = []

        # Check 1: Got 150 rankings
        if len(rankings) != 150:
            issues.append(f"Expected 150 rankings, got {len(rankings)}")
            logger.error(f"ERROR: Expected 150 rankings, got {len(rankings)}")
        else:
            logger.info("PASS: Got exactly 150 rankings")

        # Check 2: Rankings are sequential
        expected_ranks = list(range(1, 151))
        actual_ranks = [r.rank_national for r in rankings]

        if actual_ranks != expected_ranks:
            mismatches = [
                (i+1, actual_ranks[i])
                for i in range(len(actual_ranks))
                if actual_ranks[i] != expected_ranks[i]
            ]
            issues.append(f"Rankings not sequential: {len(mismatches)} mismatches")
            logger.error(f"ERROR: Found {len(mismatches)} rank mismatches")
            if len(mismatches) <= 5:
                for expected, actual in mismatches[:5]:
                    logger.error(f"  Position {expected}: expected #{expected}, got #{actual}")
        else:
            logger.info("PASS: All 150 rankings are sequential (1-150)")

        # Check 3: No duplicates
        player_ids = [r.player_id for r in rankings]
        unique_ids = set(player_ids)

        if len(unique_ids) != len(player_ids):
            duplicates = len(player_ids) - len(unique_ids)
            issues.append(f"{duplicates} duplicate player IDs")
            logger.error(f"ERROR: Found {duplicates} duplicate player IDs")
        else:
            logger.info("PASS: No duplicate player IDs")

        # Check 4: All have required fields
        missing_names = [r for r in rankings if not r.player_name]
        missing_ranks = [r for r in rankings if not r.rank_national]
        missing_stars = [r for r in rankings if not r.stars]

        if missing_names:
            issues.append(f"{len(missing_names)} players missing names")
            logger.error(f"ERROR: {len(missing_names)} players missing names")
        else:
            logger.info("PASS: All players have names")

        if missing_ranks:
            issues.append(f"{len(missing_ranks)} players missing ranks")
            logger.error(f"ERROR: {len(missing_ranks)} players missing ranks")
        else:
            logger.info("PASS: All players have national ranks")

        if missing_stars:
            issues.append(f"{len(missing_stars)} players missing stars")
            logger.error(f"ERROR: {len(missing_stars)} players missing stars")
        else:
            logger.info("PASS: All players have star ratings")

        # Display sample from different pages
        logger.info("")
        logger.info("Sample players from each page:")
        logger.info("-"*60)

        # Page 1 (ranks 1-50): show #1
        logger.info(f"Page 1, Rank #1: {rankings[0].player_name} ({rankings[0].stars} stars)")

        # Page 2 (ranks 51-100): show #51
        if len(rankings) > 50:
            logger.info(f"Page 2, Rank #51: {rankings[50].player_name} ({rankings[50].stars} stars)")

        # Page 3 (ranks 101-150): show #101
        if len(rankings) > 100:
            logger.info(f"Page 3, Rank #101: {rankings[100].player_name} ({rankings[100].stars} stars)")

        logger.info("")

        if issues:
            logger.warning("="*60)
            logger.warning("ISSUES FOUND:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            logger.warning("="*60)
            return False
        else:
            logger.info("="*60)
            logger.info("ALL PAGINATION CHECKS PASSED")
            logger.info("="*60)
            return True

    except Exception as e:
        logger.error("="*60)
        logger.error("TEST FAILED WITH EXCEPTION")
        logger.error("="*60)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main entry point."""
    success = await test_pagination()

    if success:
        logger.info("")
        logger.info("PAGINATION TEST PASSED - Multi-page fetching works correctly!")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("PAGINATION TEST FAILED - See errors above")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
