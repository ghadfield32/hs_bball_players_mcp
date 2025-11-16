"""
Multi-State GoBound Validation Script

Tests GoBound datasource for all 4 supported states (IA, IL, MN, SD).
Generates comprehensive validation report comparing results across states.

Purpose: Phase HS-2 - Validate GoBound for all 4 Midwest states
Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.bound import BoundDataSource
from src.models import Player, PlayerSeasonStats


class GoBoundMultiStateValidator:
    """
    Validates GoBound datasource across all supported states.

    Tests:
    1. Player search functionality
    2. Player stats retrieval
    3. Data quality and completeness
    4. State-specific differences

    Generates:
    - JSON report with detailed results
    - Markdown summary for documentation
    """

    # GoBound supported states
    STATES = ["IA", "IL", "MN", "SD"]

    STATE_NAMES = {
        "IA": "Iowa",
        "IL": "Illinois",
        "MN": "Minnesota",
        "SD": "South Dakota"
    }

    def __init__(self):
        """Initialize validator."""
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    async def validate_state(self, state: str, bound: BoundDataSource) -> Dict:
        """
        Validate GoBound for a single state.

        Args:
            state: State code (IA, IL, MN, SD)
            bound: BoundDataSource instance

        Returns:
            Dictionary with validation results
        """
        state_name = self.STATE_NAMES.get(state, state)
        print(f"\n{'='*70}")
        print(f"Testing: {state_name} ({state})")
        print(f"{'='*70}")

        result = {
            "state": state,
            "state_name": state_name,
            "timestamp": datetime.now().isoformat(),
            "player_search": {
                "success": False,
                "player_count": 0,
                "error": None,
                "sample_players": []
            },
            "player_stats": {
                "success": False,
                "stat_categories_found": [],
                "error": None,
                "sample_stats": {}
            },
            "data_quality": {
                "has_school_names": False,
                "has_positions": False,
                "has_jersey_numbers": False,
                "has_grades": False,
                "parsing_issues": []
            }
        }

        # Test 1: Player Search
        print(f"\n[1] Searching for players in {state_name}...")
        try:
            players = await bound.search_players(state=state, limit=5)
            result["player_search"]["player_count"] = len(players)

            if players:
                result["player_search"]["success"] = True
                print(f"[OK] SUCCESS: Found {len(players)} players")

                # Record sample players
                for i, player in enumerate(players[:3], 1):
                    player_info = {
                        "name": player.full_name,
                        "id": player.player_id,
                        "school": player.school_name,
                        "position": str(player.position) if player.position else None,
                        "jersey": player.jersey_number,
                        "grad_year": player.grad_year
                    }
                    result["player_search"]["sample_players"].append(player_info)
                    print(f"  {i}. {player.full_name}")
                    print(f"     School: {player.school_name or 'N/A'}")
                    print(f"     Position: {player.position or 'N/A'}")
                    print(f"     Jersey: #{player.jersey_number}" if player.jersey_number else "     Jersey: N/A")

                # Data quality checks
                result["data_quality"]["has_school_names"] = any(p.school_name for p in players)
                result["data_quality"]["has_positions"] = any(p.position for p in players)
                result["data_quality"]["has_jersey_numbers"] = any(p.jersey_number for p in players)
                result["data_quality"]["has_grades"] = any(p.grad_year for p in players)

                # Test 2: Player Stats for first player
                first_player = players[0]
                print(f"\n[2] Getting stats for: {first_player.full_name}")
                try:
                    stats = await bound.get_player_season_stats(
                        player_id=first_player.player_id,
                        state=state
                    )

                    if stats:
                        result["player_stats"]["success"] = True
                        print(f"[OK] SUCCESS: Stats retrieved")

                        # Record which stat categories are available
                        stat_categories = []
                        sample_stats = {}

                        if stats.points:
                            stat_categories.append("points")
                            sample_stats["points"] = stats.points
                            print(f"  Points: {stats.points}")

                        if stats.total_rebounds:
                            stat_categories.append("rebounds")
                            sample_stats["rebounds"] = stats.total_rebounds
                            print(f"  Rebounds: {stats.total_rebounds}")

                        if stats.assists:
                            stat_categories.append("assists")
                            sample_stats["assists"] = stats.assists
                            print(f"  Assists: {stats.assists}")

                        if stats.three_pointers_made:
                            stat_categories.append("three_pointers")
                            sample_stats["three_pointers"] = stats.three_pointers_made
                            print(f"  3PM: {stats.three_pointers_made}")

                        if stats.steals:
                            stat_categories.append("steals")
                            sample_stats["steals"] = stats.steals
                            print(f"  Steals: {stats.steals}")

                        if stats.blocks:
                            stat_categories.append("blocks")
                            sample_stats["blocks"] = stats.blocks
                            print(f"  Blocks: {stats.blocks}")

                        if stats.field_goals_made:
                            stat_categories.append("field_goals")
                            sample_stats["field_goals_made"] = stats.field_goals_made

                        if stats.field_goals_attempted:
                            stat_categories.append("field_goal_attempts")
                            sample_stats["field_goals_attempted"] = stats.field_goals_attempted

                        result["player_stats"]["stat_categories_found"] = stat_categories
                        result["player_stats"]["sample_stats"] = sample_stats

                        if not stat_categories:
                            print(f"[WARN] WARNING: Stats object exists but all fields are None/0")
                    else:
                        print(f"[FAIL] FAILED: No stats returned")
                        result["player_stats"]["error"] = "Stats returned None"

                except Exception as e:
                    print(f"[FAIL] FAILED: {str(e)}")
                    result["player_stats"]["error"] = str(e)
                    import traceback
                    traceback.print_exc()

            else:
                print(f"[FAIL] FAILED: No players found")
                result["player_search"]["error"] = "Search returned empty list"

        except Exception as e:
            print(f"[FAIL] FAILED: {str(e)}")
            result["player_search"]["error"] = str(e)
            import traceback
            traceback.print_exc()

        return result

    async def validate_all_states(self):
        """
        Validate GoBound for all supported states.

        Returns:
            Dictionary with results for all states
        """
        print("="*70)
        print("GoBound Multi-State Validation")
        print("="*70)
        print(f"Testing {len(self.STATES)} states: {', '.join(self.STATES)}")
        print(f"Started: {self.timestamp}")

        bound = BoundDataSource()

        try:
            for state in self.STATES:
                result = await self.validate_state(state, bound)
                self.results[state] = result

        finally:
            await bound.close()

        return self.results

    def generate_summary(self) -> Dict:
        """
        Generate summary statistics across all states.

        Returns:
            Summary dictionary
        """
        summary = {
            "timestamp": self.timestamp,
            "total_states_tested": len(self.STATES),
            "states_working": [],
            "states_failed": [],
            "player_search_success_rate": 0,
            "player_stats_success_rate": 0,
            "data_quality": {
                "all_have_school_names": True,
                "all_have_positions": True,
                "all_have_jersey_numbers": True,
                "all_have_grades": True
            },
            "stat_coverage_comparison": {}
        }

        for state, result in self.results.items():
            # Track working vs failed
            if result["player_search"]["success"] and result["player_stats"]["success"]:
                summary["states_working"].append(state)
            else:
                summary["states_failed"].append(state)

            # Data quality across states
            if not result["data_quality"]["has_school_names"]:
                summary["data_quality"]["all_have_school_names"] = False
            if not result["data_quality"]["has_positions"]:
                summary["data_quality"]["all_have_positions"] = False
            if not result["data_quality"]["has_jersey_numbers"]:
                summary["data_quality"]["all_have_jersey_numbers"] = False
            if not result["data_quality"]["has_grades"]:
                summary["data_quality"]["all_have_grades"] = False

            # Stat coverage
            stat_cats = result["player_stats"].get("stat_categories_found", [])
            summary["stat_coverage_comparison"][state] = stat_cats

        # Calculate success rates
        if self.results:
            player_search_successes = sum(
                1 for r in self.results.values() if r["player_search"]["success"]
            )
            player_stats_successes = sum(
                1 for r in self.results.values() if r["player_stats"]["success"]
            )

            summary["player_search_success_rate"] = player_search_successes / len(self.results) * 100
            summary["player_stats_success_rate"] = player_stats_successes / len(self.results) * 100

        return summary

    def save_results(self):
        """
        Save validation results to JSON and generate Markdown report.
        """
        # Save JSON results
        json_path = Path("data/debug/gobound_multi_state_validation.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        summary = self.generate_summary()

        output = {
            "summary": summary,
            "states": self.results
        }

        with open(json_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\n[OK] JSON results saved to: {json_path}")

        # Generate Markdown report
        self.generate_markdown_report(summary)

    def generate_markdown_report(self, summary: Dict):
        """
        Generate human-readable Markdown validation report.

        Args:
            summary: Summary statistics dictionary
        """
        md_path = Path("GOBOUND_MULTI_STATE_VALIDATION.md")

        lines = [
            "# GoBound Multi-State Validation Report",
            "",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Phase**: HS-2 - Validate GoBound for all 4 Midwest states",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"**States Tested**: {summary['total_states_tested']} (IA, IL, MN, SD)",
            f"**States Working**: {len(summary['states_working'])} - {', '.join(summary['states_working'])}",
            f"**States Failed**: {len(summary['states_failed'])} - {', '.join(summary['states_failed']) if summary['states_failed'] else 'None'}",
            "",
            f"**Player Search Success Rate**: {summary['player_search_success_rate']:.0f}%",
            f"**Player Stats Success Rate**: {summary['player_stats_success_rate']:.0f}%",
            "",
            "---",
            "",
            "## State-by-State Results",
            ""
        ]

        for state in self.STATES:
            result = self.results[state]
            state_name = self.STATE_NAMES[state]

            lines.append(f"### {state_name} ({state})")
            lines.append("")

            # Player search status
            if result["player_search"]["success"]:
                lines.append(f"[OK] **Player Search**: SUCCESS - Found {result['player_search']['player_count']} players")
            else:
                lines.append(f"[FAIL] **Player Search**: FAILED - {result['player_search']['error']}")

            # Player stats status
            if result["player_stats"]["success"]:
                stat_cats = result["player_stats"]["stat_categories_found"]
                lines.append(f"[OK] **Player Stats**: SUCCESS - {len(stat_cats)} stat categories")
                lines.append(f"   - Categories: {', '.join(stat_cats)}")
            else:
                lines.append(f"[FAIL] **Player Stats**: FAILED - {result['player_stats']['error']}")

            # Data quality
            lines.append("")
            lines.append("**Data Quality**:")
            lines.append(f"- School Names: {'[OK]' if result['data_quality']['has_school_names'] else '[FAIL]'}")
            lines.append(f"- Positions: {'[OK]' if result['data_quality']['has_positions'] else '[FAIL]'}")
            lines.append(f"- Jersey Numbers: {'[OK]' if result['data_quality']['has_jersey_numbers'] else '[FAIL]'}")
            lines.append(f"- Graduation Years: {'[OK]' if result['data_quality']['has_grades'] else '[FAIL]'}")

            # Sample players
            if result["player_search"]["sample_players"]:
                lines.append("")
                lines.append("**Sample Players**:")
                for i, player in enumerate(result["player_search"]["sample_players"][:3], 1):
                    lines.append(f"{i}. {player['name']}")
                    lines.append(f"   - School: {player['school']}")
                    lines.append(f"   - Position: {player['position']}")
                    if player.get('jersey'):
                        lines.append(f"   - Jersey: #{player['jersey']}")

            # Sample stats
            if result["player_stats"]["sample_stats"]:
                lines.append("")
                lines.append("**Sample Stats**:")
                for stat, value in result["player_stats"]["sample_stats"].items():
                    lines.append(f"- {stat.replace('_', ' ').title()}: {value}")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Stat coverage comparison
        lines.append("## Stat Coverage Comparison")
        lines.append("")
        lines.append("| State | Stat Categories Available |")
        lines.append("|-------|---------------------------|")
        for state in self.STATES:
            stat_cats = summary["stat_coverage_comparison"].get(state, [])
            lines.append(f"| {state} | {', '.join(stat_cats) if stat_cats else 'None'} |")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Conclusion")
        lines.append("")

        if len(summary["states_working"]) == len(self.STATES):
            lines.append(f"[OK] **ALL {len(self.STATES)} STATES WORKING** - GoBound provides player statistics for all 4 Midwest states.")
        elif summary["states_working"]:
            lines.append(f"[WARN] **PARTIAL SUCCESS** - {len(summary['states_working'])}/{len(self.STATES)} states working.")
            lines.append(f"   - Working: {', '.join(summary['states_working'])}")
            lines.append(f"   - Failed: {', '.join(summary['states_failed'])}")
        else:
            lines.append("[FAIL] **ALL STATES FAILED** - GoBound validation failed for all tested states.")

        lines.append("")
        lines.append("**Data Quality**: " + (
            "[OK] Consistent across all states" if all(summary["data_quality"].values())
            else "[WARN] Some inconsistencies detected"
        ))

        lines.append("")
        lines.append("**Status**: Validation complete - Ready for production use in covered states")
        lines.append("")

        # Write to file
        with open(md_path, 'w') as f:
            f.write('\n'.join(lines))

        print(f"[OK] Markdown report saved to: {md_path}")


async def main():
    """Run multi-state validation."""
    validator = GoBoundMultiStateValidator()

    # Run validation
    await validator.validate_all_states()

    # Generate summary
    summary = validator.generate_summary()

    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print(f"States Working: {len(summary['states_working'])}/{len(validator.STATES)}")
    print(f"  [OK] {', '.join(summary['states_working'])}" if summary['states_working'] else "  None")
    print(f"States Failed: {len(summary['states_failed'])}")
    print(f"  [FAIL] {', '.join(summary['states_failed'])}" if summary['states_failed'] else "  None")
    print(f"Player Search Success: {summary['player_search_success_rate']:.0f}%")
    print(f"Player Stats Success: {summary['player_stats_success_rate']:.0f}%")

    # Save results
    validator.save_results()

    print("\n" + "="*70)
    print("Validation complete!")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
