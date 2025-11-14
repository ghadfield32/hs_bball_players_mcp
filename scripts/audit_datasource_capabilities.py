"""
Datasource Capabilities Auditor

Comprehensive tool to audit datasource capabilities, historical ranges,
filters, and data completeness. Generates JSON reports for analysis.

Usage:
    python scripts/audit_datasource_capabilities.py --source ihsa
    python scripts/audit_datasource_capabilities.py --source iowa_ihsaa
    python scripts/audit_datasource_capabilities.py --all
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.base import BaseDataSource
from src.datasources.us.illinois_ihsa import IllinoisIHSADataSource
from src.datasources.us.iowa_ihsaa import IowaIHSAADataSource
from src.datasources.us.south_dakota_sdhsaa import SouthDakotaSdhsaaDataSource
from src.datasources.us.wisconsin_wiaa import WIAADataSource
from src.datasources.us.wisconsin_maxpreps import MaxPrepsWisconsinDataSource

# Phase 16 adapters
from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.oregon_osaa import OregonOSAADataSource
from src.datasources.us.nevada_niaa import NevadaNIAADataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.vendors.fibalivestats_federation import FIBALiveStatsFederationDataSource

from src.models import DataSourceType
from src.utils import get_logger

logger = get_logger(__name__)


class DatasourceAuditor:
    """Comprehensive auditor for datasource capabilities."""

    def __init__(self, output_dir: str = "data/audit"):
        """
        Initialize auditor.

        Args:
            output_dir: Directory to save audit reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def audit_datasource(self, source: BaseDataSource) -> Dict[str, Any]:
        """
        Comprehensive audit of a datasource.

        Args:
            source: Datasource to audit

        Returns:
            Audit report dictionary
        """
        logger.info(f"Starting audit of {source.source_name}")

        report = {
            "source_id": source.source_type.value,
            "source_name": source.source_name,
            "audit_timestamp": datetime.utcnow().isoformat(),
            "capabilities": {},
            "historical_range": {},
            "filters": {},
            "data_samples": {},
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Test capabilities
        await self._audit_capabilities(source, report)

        # Test historical range
        await self._audit_historical_range(source, report)

        # Discover and test filters
        await self._audit_filters(source, report)

        # Sample data for completeness
        await self._audit_data_completeness(source, report)

        # Generate recommendations
        self._generate_recommendations(report)

        logger.info(f"Completed audit of {source.source_name}")
        return report

    async def _audit_capabilities(self, source: BaseDataSource, report: Dict):
        """Test basic capabilities (what methods work)."""
        capabilities = {
            "has_player_stats": False,
            "has_schedules": False,
            "has_brackets": False,
            "has_leaderboards": False,
            "has_team_stats": False,
            "has_game_stats": False,
        }

        # Test health check
        try:
            is_healthy = await source.health_check()
            capabilities["health_check"] = is_healthy
            if not is_healthy:
                report["warnings"].append("Health check failed - source may be down")
        except Exception as e:
            capabilities["health_check"] = False
            report["issues"].append(f"Health check error: {str(e)}")

        # Test player search
        try:
            players = await source.search_players(limit=1)
            capabilities["has_player_stats"] = len(players) > 0
            if len(players) > 0:
                capabilities["player_search_works"] = True
        except NotImplementedError:
            capabilities["player_search_works"] = False
        except Exception as e:
            capabilities["player_search_works"] = False
            report["issues"].append(f"Player search error: {str(e)}")

        # Test leaderboard
        try:
            leaderboard = await source.get_leaderboard(limit=1)
            capabilities["has_leaderboards"] = len(leaderboard) > 0
        except NotImplementedError:
            pass
        except Exception as e:
            report["warnings"].append(f"Leaderboard test error: {str(e)}")

        # Test schedules/games
        try:
            games = await source.get_games(limit=1)
            capabilities["has_schedules"] = len(games) > 0
        except NotImplementedError:
            pass
        except Exception as e:
            report["warnings"].append(f"Games/schedules test error: {str(e)}")

        # Check for bracket methods (association adapters)
        if hasattr(source, "get_tournament_brackets"):
            capabilities["has_brackets"] = True
            try:
                # Try current season
                current_season = "2024-25"
                brackets = await source.get_tournament_brackets(season=current_season)
                if isinstance(brackets, dict):
                    capabilities["bracket_count_sample"] = len(brackets.get("games", []))
            except Exception as e:
                report["warnings"].append(f"Bracket test error: {str(e)}")

        report["capabilities"] = capabilities

    async def _audit_historical_range(self, source: BaseDataSource, report: Dict):
        """
        Test historical data availability.

        Try seasons from 2025 back to 2010.
        """
        logger.info(f"Testing historical range for {source.source_name}")

        historical = {
            "min_year": None,
            "max_year": None,
            "tested_seasons": [],
            "available_seasons": [],
            "unavailable_seasons": [],
        }

        # Test seasons from 2024-25 back to 2010-11
        seasons_to_test = [f"{year}-{str(year+1)[-2:]}" for year in range(2024, 2009, -1)]

        for season in seasons_to_test:
            try:
                # Try to get data for this season
                if hasattr(source, "get_tournament_brackets"):
                    data = await source.get_tournament_brackets(season=season)
                else:
                    data = await source.get_games(season=season, limit=1)

                historical["tested_seasons"].append(season)

                # Check if data exists
                has_data = False
                if isinstance(data, dict):
                    has_data = len(data.get("games", [])) > 0
                elif isinstance(data, list):
                    has_data = len(data) > 0

                if has_data:
                    historical["available_seasons"].append(season)
                    year = int(season.split("-")[0])
                    if historical["max_year"] is None or year > historical["max_year"]:
                        historical["max_year"] = year
                    if historical["min_year"] is None or year < historical["min_year"]:
                        historical["min_year"] = year
                else:
                    historical["unavailable_seasons"].append(season)

            except Exception as e:
                historical["unavailable_seasons"].append(season)
                logger.debug(f"Season {season} unavailable: {e}")

            # Rate limiting - wait between requests
            await asyncio.sleep(1)

        if historical["min_year"] and historical["max_year"]:
            historical["years_available"] = historical["max_year"] - historical["min_year"] + 1
        else:
            historical["years_available"] = 0
            report["warnings"].append("No historical data found")

        report["historical_range"] = historical

    async def _audit_filters(self, source: BaseDataSource, report: Dict):
        """
        Discover and test available filters.

        Check method signatures and test common filters.
        """
        logger.info(f"Testing filters for {source.source_name}")

        filters = {
            "discovered": [],
            "tested": [],
            "working": [],
            "broken": [],
        }

        # Check method signatures for filter parameters
        import inspect

        # Get games method signature
        if hasattr(source, "get_games"):
            sig = inspect.signature(source.get_games)
            filters["discovered"].extend([p for p in sig.parameters.keys() if p != "self"])

        # Get tournament brackets signature
        if hasattr(source, "get_tournament_brackets"):
            sig = inspect.signature(source.get_tournament_brackets)
            filters["discovered"].extend([p for p in sig.parameters.keys() if p != "self"])

        # Get search players signature
        if hasattr(source, "search_players"):
            sig = inspect.signature(source.search_players)
            filters["discovered"].extend([p for p in sig.parameters.keys() if p != "self"])

        # Remove duplicates
        filters["discovered"] = list(set(filters["discovered"]))

        # Test common filters
        common_filters = {
            "season": "2024-25",
            "gender": "Boys",
            "limit": 1,
        }

        # Test bracket-specific filters
        if hasattr(source, "get_tournament_brackets"):
            # Check if source has classes/divisions
            if hasattr(source, "CLASSES"):
                common_filters["class_name"] = source.CLASSES[0] if source.CLASSES else None
            if hasattr(source, "DIVISIONS"):
                common_filters["division"] = source.DIVISIONS[0] if source.DIVISIONS else None

        for filter_name, filter_value in common_filters.items():
            if filter_name in filters["discovered"] and filter_value is not None:
                try:
                    # Test the filter
                    if hasattr(source, "get_tournament_brackets") and filter_name in [
                        "season",
                        "class_name",
                        "division",
                        "gender",
                    ]:
                        kwargs = {filter_name: filter_value}
                        result = await source.get_tournament_brackets(**kwargs)
                        filters["tested"].append(filter_name)
                        filters["working"].append(filter_name)
                    elif hasattr(source, "get_games"):
                        kwargs = {filter_name: filter_value}
                        result = await source.get_games(**kwargs)
                        filters["tested"].append(filter_name)
                        filters["working"].append(filter_name)

                except Exception as e:
                    filters["tested"].append(filter_name)
                    filters["broken"].append(filter_name)
                    report["issues"].append(f"Filter '{filter_name}' error: {str(e)}")

                # Rate limiting
                await asyncio.sleep(0.5)

        report["filters"] = filters

    async def _audit_data_completeness(self, source: BaseDataSource, report: Dict):
        """
        Sample data to check completeness.

        Get a small sample and validate structure.
        """
        logger.info(f"Sampling data for {source.source_name}")

        samples = {
            "games_sample_count": 0,
            "players_sample_count": 0,
            "teams_sample_count": 0,
            "has_complete_game_data": False,
            "has_complete_player_data": False,
        }

        # Sample games
        try:
            games = await source.get_games(limit=5)
            samples["games_sample_count"] = len(games)

            if len(games) > 0:
                game = games[0]
                # Check for required fields
                has_complete = all(
                    [
                        game.game_id,
                        game.home_team_name or game.away_team_name,
                        game.season,
                    ]
                )
                samples["has_complete_game_data"] = has_complete
                samples["game_sample"] = {
                    "game_id": game.game_id,
                    "home_team": game.home_team_name,
                    "away_team": game.away_team_name,
                    "season": game.season,
                }

        except Exception as e:
            logger.debug(f"Could not sample games: {e}")

        # Sample players
        try:
            players = await source.search_players(limit=5)
            samples["players_sample_count"] = len(players)

            if len(players) > 0:
                player = players[0]
                has_complete = all([player.player_id, player.full_name])
                samples["has_complete_player_data"] = has_complete
                samples["player_sample"] = {
                    "player_id": player.player_id,
                    "name": player.full_name,
                    "school": player.school_name,
                }

        except Exception as e:
            logger.debug(f"Could not sample players: {e}")

        report["data_samples"] = samples

    def _generate_recommendations(self, report: Dict):
        """Generate recommendations based on audit findings."""
        recommendations = []

        # Check historical range
        if report["historical_range"].get("years_available", 0) < 5:
            recommendations.append(
                "Historical data limited (<5 years). Consider documenting range in capabilities."
            )

        # Check capabilities
        caps = report["capabilities"]
        if not caps.get("has_player_stats") and not caps.get("has_schedules"):
            recommendations.append(
                "No player stats or schedules available. May need to find alternative datasource."
            )

        # Check filters
        if len(report["filters"].get("broken", [])) > 0:
            recommendations.append(
                f"Filters broken: {', '.join(report['filters']['broken'])}. Need investigation."
            )

        # Check issues
        if len(report["issues"]) > 3:
            recommendations.append(
                f"Multiple issues found ({len(report['issues'])}). Prioritize fixing."
            )

        report["recommendations"] = recommendations

    def save_report(self, report: Dict, source_id: str):
        """Save audit report to JSON file."""
        output_file = self.output_dir / f"{source_id}_audit.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Saved audit report to {output_file}")

    async def audit_all_sources(self, sources: List[BaseDataSource]) -> List[Dict]:
        """Audit multiple datasources sequentially."""
        reports = []

        for source in sources:
            try:
                report = await self.audit_datasource(source)
                self.save_report(report, source.source_type.value)
                reports.append(report)

                # Wait between sources to respect rate limits
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Failed to audit {source.source_name}: {e}")

        return reports


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit datasource capabilities")
    parser.add_argument(
        "--source",
        type=str,
        choices=[
            "ihsa", "iowa_ihsaa", "sdhsaa", "wiaa", "maxpreps_wi",
            "aia", "osaa", "niaa", "wiaa_wa", "ihsaa_id",
            "fiba_federation", "all", "phase16"
        ],
        help="Datasource to audit",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/audit",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    auditor = DatasourceAuditor(output_dir=args.output)

    # Select sources to audit
    sources = []
    if args.source == "ihsa":
        sources = [IllinoisIHSADataSource()]
    elif args.source == "iowa_ihsaa":
        sources = [IowaIHSAADataSource()]
    elif args.source == "sdhsaa":
        sources = [SouthDakotaSdhsaaDataSource()]
    elif args.source == "wiaa":
        sources = [WIAADataSource()]
    elif args.source == "maxpreps_wi":
        sources = [MaxPrepsWisconsinDataSource()]
    # Phase 16 adapters
    elif args.source == "aia":
        sources = [ArizonaAIADataSource()]
    elif args.source == "osaa":
        sources = [OregonOSAADataSource()]
    elif args.source == "niaa":
        sources = [NevadaNIAADataSource()]
    elif args.source == "wiaa_wa":
        sources = [WashingtonWIAADataSource()]
    elif args.source == "ihsaa_id":
        sources = [IdahoIHSAADataSource()]
    elif args.source == "fiba_federation":
        # Test with Egypt federation as example
        sources = [FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25")]
    elif args.source == "phase16":
        # All Phase 16 adapters
        sources = [
            ArizonaAIADataSource(),
            OregonOSAADataSource(),
            NevadaNIAADataSource(),
            WashingtonWIAADataSource(),
            IdahoIHSAADataSource(),
            FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25"),
        ]
    elif args.source == "all":
        sources = [
            IllinoisIHSADataSource(),
            IowaIHSAADataSource(),
            SouthDakotaSdhsaaDataSource(),
            WIAADataSource(),
            MaxPrepsWisconsinDataSource(),
            # Phase 16
            ArizonaAIADataSource(),
            OregonOSAADataSource(),
            NevadaNIAADataSource(),
            WashingtonWIAADataSource(),
            IdahoIHSAADataSource(),
            FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25"),
        ]
    else:
        print("Please specify a datasource to audit with --source")
        return

    # Run audit
    reports = await auditor.audit_all_sources(sources)

    # Print summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    for report in reports:
        print(f"\n{report['source_name']}:")
        print(f"  Historical Range: {report['historical_range'].get('years_available', 0)} years")
        print(f"  Filters Working: {len(report['filters'].get('working', []))}")
        print(f"  Issues: {len(report['issues'])}")
        print(f"  Recommendations: {len(report['recommendations'])}")

    print(f"\nDetailed reports saved to: {auditor.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
