"""
Comprehensive Datasource Audit - Systematic Testing

Tests ALL datasources to create complete inventory of:
1. Which provide player statistics
2. Which states they cover
3. Data quality assessment
4. Legal/technical restrictions

Output: Complete audit report with recommendations
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

# Test states (one per region for efficiency)
TEST_STATES = {
    "IA": "Iowa (GoBound known working)",
    "TX": "Texas (RankOne known non-working)",
    "CA": "California (Largest state)",
    "NY": "New York (Major basketball state)",
    "GA": "Georgia (Southeast)",
}


class DataSourceAudit:
    """Comprehensive datasource audit."""

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    async def test_datasource_simple(
        self,
        name: str,
        module_path: str,
        class_name: str,
        test_state: str
    ) -> Dict:
        """
        Simple test of datasource capability.

        Returns:
            Dict with status, player_search, player_stats flags
        """
        result = {
            "name": name,
            "module": module_path,
            "class": class_name,
            "test_state": test_state,
            "status": "unknown",
            "player_search_works": False,
            "player_stats_works": False,
            "error": None,
            "notes": [],
        }

        try:
            # Dynamic import
            module_parts = module_path.split('.')
            module = __import__(module_path, fromlist=[class_name])
            datasource_class = getattr(module, class_name)

            # Initialize
            try:
                datasource = datasource_class()
            except Exception as e:
                result["status"] = "init_failed"
                result["error"] = f"Init failed: {str(e)[:100]}"
                return result

            # Test player search
            try:
                players = await datasource.search_players(
                    state=test_state,
                    limit=3
                )

                if players and len(players) > 0:
                    result["player_search_works"] = True
                    result["notes"].append(f"Found {len(players)} players")

                    # Test player stats for first player
                    try:
                        first_player = players[0]
                        stats = await datasource.get_player_season_stats(
                            player_id=first_player.player_id,
                            state=test_state
                        )

                        if stats:
                            result["player_stats_works"] = True
                            result["notes"].append("Stats retrieved successfully")
                            # Check if stats have actual data
                            has_data = any([
                                stats.points,
                                stats.total_rebounds,
                                stats.assists
                            ])
                            if has_data:
                                result["status"] = "working"
                            else:
                                result["status"] = "empty_stats"
                                result["notes"].append("Stats object exists but empty")
                        else:
                            result["status"] = "no_stats"
                            result["notes"].append("Players found but no stats")

                    except Exception as e:
                        result["status"] = "stats_error"
                        result["error"] = f"Stats error: {str(e)[:100]}"
                        result["notes"].append("Stats retrieval failed")

                else:
                    result["status"] = "no_players"
                    result["notes"].append("Search returned empty")

            except Exception as e:
                result["status"] = "search_error"
                result["error"] = f"Search error: {str(e)[:100]}"

            # Close if method exists
            if hasattr(datasource, 'close'):
                try:
                    await datasource.close()
                except:
                    pass

        except Exception as e:
            result["status"] = "import_error"
            result["error"] = f"Import error: {str(e)[:100]}"

        return result

    async def run_audit(self):
        """Run comprehensive audit of all datasources."""
        print("="*80)
        print("COMPREHENSIVE DATASOURCE AUDIT")
        print("="*80)
        print(f"Started: {self.timestamp}\n")

        # Define all datasources to test
        datasources = [
            # US State Datasources
            ("GoBound Iowa", "src.datasources.us.bound", "BoundDataSource", "IA"),
            ("GoBound Illinois", "src.datasources.us.bound", "BoundDataSource", "IL"),
            ("RankOne Texas", "src.datasources.us.rankone", "RankOneDataSource", "TX"),
            ("Texas UIL", "src.datasources.us.texas_uil", "TexasUILDataSource", "TX"),
            ("California CIF", "src.datasources.us.california_cif_ss", "CIFSSDataSource", "CA"),
            ("Georgia GHSA", "src.datasources.us.georgia_ghsa", "GHSADataSource", "GA"),
            ("Florida FHSAA", "src.datasources.us.florida_fhsaa", "FHSAADataSource", "FL"),
            ("Kentucky KHSAA", "src.datasources.us.kentucky_khsaa", "KHSAADataSource", "KY"),
            ("Indiana IHSAA", "src.datasources.us.indiana_ihsaa", "IHSAADataSource", "IN"),
            ("Ohio OHSAA", "src.datasources.us.ohio_ohsaa", "OHSAADataSource", "OH"),
            ("MaxPreps CA", "src.datasources.us.maxpreps", "MaxPrepsDataSource", "CA"),

            # Recruiting Datasources
            ("On3", "src.datasources.recruiting.on3", "On3DataSource", None),
            ("247Sports", "src.datasources.recruiting.sports_247", "Sports247DataSource", None),
        ]

        # Run tests
        for name, module, class_name, test_state in datasources:
            print(f"\nTesting: {name}")
            print("-" * 60)

            result = await self.test_datasource_simple(
                name, module, class_name, test_state or "CA"
            )

            self.results[name] = result

            # Display result
            status = result["status"]
            if status == "working":
                print(f"[OK] WORKING - Provides player stats")
            elif status == "no_stats":
                print(f"[PARTIAL] Players only, no stats")
            elif status == "no_players":
                print(f"[NO DATA] No players found")
            elif status == "empty_stats":
                print(f"[EMPTY] Stats object but no data")
            else:
                error = result.get("error", "Unknown")
                print(f"[{status.upper()}] {error}")

            # Display notes
            for note in result.get("notes", []):
                print(f"  - {note}")

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate summary report."""
        print("\n\n" + "="*80)
        print("AUDIT SUMMARY")
        print("="*80)

        # Categorize
        working = []
        partial = []
        not_working = []
        errors = []

        for name, result in self.results.items():
            status = result["status"]
            if status == "working":
                working.append(name)
            elif status in ["no_stats", "empty_stats"]:
                partial.append(name)
            elif status in ["no_players", "no_data"]:
                not_working.append(name)
            else:
                errors.append((name, status, result.get("error", "Unknown")))

        # Display summary
        print(f"\n[OK] WORKING - Player Stats Available: {len(working)}")
        for name in working:
            print(f"  - {name}")

        print(f"\n[PARTIAL] Players Only, No Stats: {len(partial)}")
        for name in partial:
            print(f"  - {name}")

        print(f"\n[NO DATA] No Player Data: {len(not_working)}")
        for name in not_working:
            print(f"  - {name}")

        print(f"\n[ERROR] Errors: {len(errors)}")
        for name, status, error in errors:
            print(f"  - {name}: {status} - {error[:60]}")

        # Save results
        output_file = Path("data/debug/comprehensive_audit.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": self.timestamp,
                "summary": {
                    "working": len(working),
                    "partial": len(partial),
                    "not_working": len(not_working),
                    "errors": len(errors),
                },
                "results": self.results,
            }, f, indent=2, default=str)

        print(f"\n\nFull results saved to: {output_file}")


async def main():
    """Run audit."""
    audit = DataSourceAudit()
    await audit.run_audit()


if __name__ == '__main__':
    asyncio.run(main())
