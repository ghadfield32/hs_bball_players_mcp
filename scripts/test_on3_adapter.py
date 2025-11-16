"""
Test On3/Rivals Adapter

Validates:
1. Browser can load page without bot detection
2. JSON extraction works correctly
3. Player parsing populates all fields
4. Data quality is acceptable

Usage:
    python scripts/test_on3_adapter.py

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


async def test_on3_adapter():
    """Test On3/Rivals recruiting adapter."""
    from src.datasources.recruiting.on3 import On3DataSource

    logger.info("="*60)
    logger.info("Testing On3/Rivals Adapter")
    logger.info("="*60)
    logger.info("")

    on3 = On3DataSource()

    try:
        # Fetch top 10 for class of 2025
        logger.info("Fetching top 10 players for class of 2025...")
        logger.info("")

        rankings = await on3.get_rankings(class_year=2025, limit=10)

        if not rankings:
            logger.error("FAILED: No rankings returned")
            logger.error("  This means either:")
            logger.error("  1. Page failed to load")
            logger.error("  2. __NEXT_DATA__ JSON not found")
            logger.error("  3. Player parsing failed")
            return False

        logger.info(f"SUCCESS: Fetched {len(rankings)} players")
        logger.info("")

        # Display first 5
        logger.info("Top 5 Players:")
        logger.info("-"*60)
        for i, rank in enumerate(rankings[:5], 1):
            logger.info(f"{i}. {rank.player_name}")
            logger.info(f"   National Rank: #{rank.rank_national}")
            logger.info(f"   Position: {rank.position}")
            logger.info(f"   Height/Weight: {rank.height} / {rank.weight} lbs")
            logger.info(f"   Rating: {rank.rating:.2f}" if rank.rating else "   Rating: N/A")
            logger.info(f"   Stars: {rank.stars}")
            logger.info(f"   School: {rank.school}")
            if rank.city and rank.state:
                logger.info(f"   Hometown: {rank.city}, {rank.state}")
            if rank.committed_to:
                logger.info(f"   Committed: {rank.committed_to}")
            logger.info("")

        # Validation
        logger.info("="*60)
        logger.info("VALIDATION CHECKS")
        logger.info("="*60)
        logger.info("")

        issues = []

        # Check 1: All players have names
        missing_names = [r for r in rankings if not r.player_name]
        if missing_names:
            issues.append(f"{len(missing_names)} players missing names")
            logger.error(f"ERROR: {len(missing_names)} players missing names")
        else:
            logger.info("PASS: All players have names")

        # Check 2: All players have national ranks
        missing_ranks = [r for r in rankings if not r.rank_national]
        if missing_ranks:
            issues.append(f"{len(missing_ranks)} players missing national rank")
            logger.error(f"ERROR: {len(missing_ranks)} players missing national rank")
        else:
            logger.info("PASS: All players have national ranks")

        # Check 3: Players have ratings
        missing_ratings = [r for r in rankings if not r.rating]
        if missing_ratings:
            logger.warning(f"WARNING: {len(missing_ratings)} players missing ratings")
        else:
            logger.info("PASS: All players have ratings")

        # Check 4: Players have stars
        missing_stars = [r for r in rankings if not r.stars]
        if missing_stars:
            issues.append(f"{len(missing_stars)} players missing star ratings")
            logger.error(f"ERROR: {len(missing_stars)} players missing star ratings")
        else:
            logger.info("PASS: All players have star ratings")

        # Check 5: Players have positions
        missing_positions = [r for r in rankings if not r.position]
        if missing_positions:
            logger.warning(f"WARNING: {len(missing_positions)} players missing positions")
        else:
            logger.info("PASS: All players have positions")

        # Check 6: First player should be #1
        if rankings[0].rank_national != 1:
            issues.append(f"First player rank is {rankings[0].rank_national}, expected 1")
            logger.error(f"ERROR: First player rank is {rankings[0].rank_national}, expected 1")
        else:
            logger.info("PASS: First player is ranked #1")

        # Check 7: Rankings are sequential
        ranks = [r.rank_national for r in rankings if r.rank_national]
        if ranks != list(range(1, len(ranks) + 1)):
            logger.warning(f"WARNING: Rankings not perfectly sequential: {ranks}")
        else:
            logger.info("PASS: Rankings are sequential")

        # Check 8: Service is INDUSTRY
        non_industry = [r for r in rankings if r.service != "industry"]
        if non_industry:
            issues.append(f"{len(non_industry)} players have wrong service type")
            logger.error(f"ERROR: {len(non_industry)} players have wrong service type")
        else:
            logger.info("PASS: All rankings are from INDUSTRY service")

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
            logger.info("ALL VALIDATION CHECKS PASSED")
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
    success = await test_on3_adapter()

    if success:
        logger.info("")
        logger.info("TEST PASSED - On3 adapter is working correctly!")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("TEST FAILED - See errors above")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
