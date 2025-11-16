"""
Quick Test Script for 247Sports Fix

Tests the updated browser scraping implementation to verify:
1. Browser loads page without crash
2. Finds ul.rankings-page__list element
3. Extracts player items correctly
4. Parses all fields (name, rank, position, height, weight, rating, stars)

Usage:
    python scripts/test_247_fix.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_247_fix():
    """Test the 247Sports browser scraping fix."""
    from src.datasources.recruiting.sports_247 import Sports247DataSource

    logger.info("="*60)
    logger.info("Testing 247Sports Browser Scraping Fix")
    logger.info("="*60)
    logger.info("")

    # Initialize datasource
    logger.info("Initializing Sports247DataSource...")
    sports247 = Sports247DataSource()

    try:
        # Test with 2025 class, top 10 players
        logger.info("Fetching top 10 players for class of 2025...")
        logger.info("")

        rankings = await sports247.get_rankings(
            class_year=2025,
            limit=10
        )

        logger.info("")
        logger.info("="*60)
        logger.info("TEST RESULTS")
        logger.info("="*60)
        logger.info("")

        if not rankings:
            logger.error("❌ TEST FAILED: No rankings returned")
            logger.error("   This means the selector or parsing still has issues")
            return False

        logger.info(f"✅ SUCCESS: Fetched {len(rankings)} players")
        logger.info("")

        # Display first 5 players to verify data quality
        logger.info("Top 5 Players:")
        logger.info("-"*60)
        for i, rank in enumerate(rankings[:5], 1):
            logger.info(f"{i}. {rank.player_name}")
            logger.info(f"   Rank: {rank.rank_national}")
            logger.info(f"   Position: {rank.position}")
            logger.info(f"   Height/Weight: {rank.height} / {rank.weight} lbs")
            logger.info(f"   Rating: {rank.rating}")
            logger.info(f"   Stars: {rank.stars}★")
            logger.info(f"   School: {rank.school} ({rank.city}, {rank.state})")
            if rank.committed_to:
                logger.info(f"   Committed: {rank.committed_to}")
            logger.info("")

        # Validation checks
        logger.info("="*60)
        logger.info("VALIDATION CHECKS")
        logger.info("="*60)
        logger.info("")

        issues = []

        # Check 1: All players have names
        missing_names = [r for r in rankings if not r.player_name]
        if missing_names:
            issues.append(f"❌ {len(missing_names)} players missing names")
        else:
            logger.info("✅ All players have names")

        # Check 2: All players have ranks
        missing_ranks = [r for r in rankings if not r.rank_national]
        if missing_ranks:
            issues.append(f"❌ {len(missing_ranks)} players missing national rank")
        else:
            logger.info("✅ All players have national ranks")

        # Check 3: Players have ratings
        missing_ratings = [r for r in rankings if not r.rating]
        if missing_ratings:
            issues.append(f"⚠️  {len(missing_ratings)} players missing ratings")
        else:
            logger.info("✅ All players have ratings")

        # Check 4: Players have stars
        missing_stars = [r for r in rankings if not r.stars]
        if missing_stars:
            issues.append(f"⚠️  {len(missing_stars)} players missing star ratings")
        else:
            logger.info("✅ All players have star ratings")

        # Check 5: Players have positions
        missing_positions = [r for r in rankings if not r.position]
        if missing_positions:
            logger.info(f"⚠️  {len(missing_positions)} players missing positions (may be normal)")
        else:
            logger.info("✅ All players have positions")

        # Check 6: First player should be #1
        if rankings[0].rank_national != 1:
            issues.append(f"❌ First player rank is {rankings[0].rank_national}, expected 1")
        else:
            logger.info("✅ First player is ranked #1")

        # Check 7: Rankings are sequential
        ranks = [r.rank_national for r in rankings if r.rank_national]
        if ranks != list(range(1, len(ranks) + 1)):
            logger.info(f"⚠️  Rankings not perfectly sequential: {ranks}")
        else:
            logger.info("✅ Rankings are sequential")

        logger.info("")

        if issues:
            logger.warning("="*60)
            logger.warning("ISSUES FOUND:")
            for issue in issues:
                logger.warning(f"  {issue}")
            logger.warning("="*60)
            return False
        else:
            logger.info("="*60)
            logger.info("✅ ALL VALIDATION CHECKS PASSED")
            logger.info("="*60)
            return True

    except Exception as e:
        logger.error("="*60)
        logger.error("❌ TEST FAILED WITH EXCEPTION")
        logger.error("="*60)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        await sports247.close()


async def main():
    """Main entry point."""
    success = await test_247_fix()

    if success:
        logger.info("")
        logger.info("🎉 TEST PASSED - 247Sports fix is working!")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("❌ TEST FAILED - See errors above")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
