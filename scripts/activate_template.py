"""
Template Adapter Activation Helper

Interactive script to help activate template adapters following the
7-step process in docs/TEMPLATE_ADAPTER_ACTIVATION.md

Usage:
    python scripts/activate_template.py <adapter_name>

Examples:
    python scripts/activate_template.py angt
    python scripts/activate_template.py osba
    python scripts/activate_template.py playhq
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Template adapter configurations
TEMPLATES = {
    "angt": {
        "name": "ANGT",
        "full_name": "Adidas Next Generation Tournament",
        "region": "Europe",
        "base_url": "https://www.euroleaguebasketball.net/next-generation",
        "file_path": "src/datasources/europe/angt.py",
        "test_file": "tests/test_datasources/test_angt.py",
        "priority": "HIGH",
        "description": "Europe U18 elite tournament",
        "todos": [
            "Visit https://www.euroleaguebasketball.net/next-generation",
            "Inspect HTML structure for stats tables",
            "Identify URL patterns (/competition, /players, /games)",
            "Note column names (Player, Team, Points, PIR)",
            "Check robots.txt permissions",
            "Update URLs in src/datasources/europe/angt.py (lines ~78-85)",
            "Update column mapping if needed",
            "Create test file: tests/test_datasources/test_angt.py",
            "Run tests: pytest tests/test_datasources/test_angt.py -v",
            "Uncomment in src/services/aggregator.py",
            "Update config/sources.yaml: template → active",
            "Update PROJECT_LOG.md with activation details",
        ],
    },
    "osba": {
        "name": "OSBA",
        "full_name": "Ontario Scholastic Basketball Association",
        "region": "Canada",
        "base_url": "https://www.osba.ca",
        "file_path": "src/datasources/canada/osba.py",
        "test_file": "tests/test_datasources/test_osba.py",
        "priority": "HIGH",
        "description": "Ontario prep basketball",
        "todos": [
            "Visit https://www.osba.ca",
            "Inspect stats/leaders pages",
            "Identify division structure (U17, U19, Prep)",
            "Note URL patterns for stats and schedules",
            "Check robots.txt permissions",
            "Update URLs in src/datasources/canada/osba.py (lines ~78-85)",
            "Update column mapping if needed",
            "Create test file: tests/test_datasources/test_osba.py",
            "Run tests: pytest tests/test_datasources/test_osba.py -v",
            "Uncomment in src/services/aggregator.py",
            "Update config/sources.yaml: template → active",
            "Update PROJECT_LOG.md with activation details",
        ],
    },
    "playhq": {
        "name": "PlayHQ",
        "full_name": "PlayHQ Basketball Australia",
        "region": "Australia",
        "base_url": "https://www.playhq.com/basketball",
        "file_path": "src/datasources/australia/playhq.py",
        "test_file": "tests/test_datasources/test_playhq.py",
        "priority": "HIGH",
        "description": "Australian junior basketball",
        "todos": [
            "Visit https://www.playhq.com/basketball",
            "Inspect competition listings and stats pages",
            "Identify U16/U18 Championships structure",
            "Note URL patterns: /competitions/{comp_id}/players",
            "Check robots.txt permissions",
            "Update URLs in src/datasources/australia/playhq.py (lines ~83-97)",
            "Update competition ID patterns",
            "Create test file: tests/test_datasources/test_playhq.py",
            "Run tests: pytest tests/test_datasources/test_playhq.py -v",
            "Uncomment in src/services/aggregator.py",
            "Update config/sources.yaml: template → active",
            "Update PROJECT_LOG.md with activation details",
        ],
    },
    "ote": {
        "name": "OTE",
        "full_name": "Overtime Elite",
        "region": "US",
        "base_url": "https://overtimeelite.com",
        "file_path": "src/datasources/us/ote.py",
        "test_file": "tests/test_datasources/test_ote.py",
        "priority": "MEDIUM",
        "description": "US prep league",
        "todos": [
            "Visit https://overtimeelite.com",
            "Inspect stats/players page structure",
            "Check for JavaScript rendering requirements",
            "Note URL patterns for teams and schedules",
            "Check robots.txt permissions",
            "Update URLs in src/datasources/us/ote.py (lines ~74-78)",
            "Enable browser automation if JS rendering needed",
            "Create test file: tests/test_datasources/test_ote.py",
            "Run tests: pytest tests/test_datasources/test_ote.py -v",
            "Uncomment in src/services/aggregator.py",
            "Update config/sources.yaml: template → active",
            "Update PROJECT_LOG.md with activation details",
        ],
    },
    "grind_session": {
        "name": "Grind Session",
        "full_name": "Grind Session",
        "region": "US",
        "base_url": "https://thegrindsession.com",
        "file_path": "src/datasources/us/grind_session.py",
        "test_file": "tests/test_datasources/test_grind_session.py",
        "priority": "MEDIUM",
        "description": "US prep tournament series",
        "todos": [
            "Visit https://thegrindsession.com",
            "Inspect event pages and stats sections",
            "Identify event-specific URL patterns",
            "Note column names for stats tables",
            "Check robots.txt permissions",
            "Update URLs in src/datasources/us/grind_session.py (lines ~78-85)",
            "Update event URL pattern logic",
            "Create test file: tests/test_datasources/test_grind_session.py",
            "Run tests: pytest tests/test_datasources/test_grind_session.py -v",
            "Uncomment in src/services/aggregator.py",
            "Update config/sources.yaml: template → active",
            "Update PROJECT_LOG.md with activation details",
        ],
    },
}


def print_adapter_info(adapter_key: str):
    """Print information about a template adapter."""
    config = TEMPLATES[adapter_key]

    print()
    print("=" * 70)
    print(f"TEMPLATE ADAPTER: {config['name']}")
    print("=" * 70)
    print()
    print(f"Full Name:    {config['full_name']}")
    print(f"Region:       {config['region']}")
    print(f"Priority:     {config['priority']}")
    print(f"Description:  {config['description']}")
    print()
    print(f"Base URL:     {config['base_url']}")
    print(f"Adapter File: {config['file_path']}")
    print(f"Test File:    {config['test_file']}")
    print()


def print_activation_checklist(adapter_key: str):
    """Print activation checklist for an adapter."""
    config = TEMPLATES[adapter_key]

    print("ACTIVATION CHECKLIST")
    print("-" * 70)
    print()

    for i, todo in enumerate(config["todos"], 1):
        print(f"  {i:2d}. [ ] {todo}")

    print()
    print("-" * 70)
    print()
    print("ESTIMATED TIME: 2-4 hours")
    print()
    print("For detailed instructions, see:")
    print("  docs/TEMPLATE_ADAPTER_ACTIVATION.md")
    print()


def print_next_steps(adapter_key: str):
    """Print next steps after activation."""
    config = TEMPLATES[adapter_key]

    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Start by visiting the website:")
    print(f"   {config['base_url']}")
    print()
    print("2. Open the adapter file:")
    print(f"   {config['file_path']}")
    print()
    print("3. Look for TODO comments and update URLs")
    print()
    print("4. Create test file:")
    print(f"   {config['test_file']}")
    print()
    print("5. Run tests:")
    print(f"   pytest {config['test_file']} -v")
    print()
    print("6. Uncomment in aggregator:")
    print("   src/services/aggregator.py")
    print()
    print("7. Update sources.yaml status: template → active")
    print()
    print("8. Document in PROJECT_LOG.md")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Template adapter activation helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available templates:
  {', '.join(TEMPLATES.keys())}

Priority order:
  HIGH:   angt, osba, playhq (activate first)
  MEDIUM: ote, grind_session (activate after high-priority)

Examples:
  python scripts/activate_template.py angt
  python scripts/activate_template.py osba
  python scripts/activate_template.py playhq
        """,
    )

    parser.add_argument("adapter", choices=TEMPLATES.keys(), help="Template adapter to activate")

    parser.add_argument(
        "--list", action="store_true", help="List all available templates and exit"
    )

    args = parser.parse_args()

    if args.list:
        print()
        print("=" * 70)
        print("AVAILABLE TEMPLATE ADAPTERS")
        print("=" * 70)
        print()

        for key, config in TEMPLATES.items():
            priority_icon = "🔴" if config["priority"] == "HIGH" else "🟡"
            print(
                f"{priority_icon} {config['name']:15} - {config['description']} ({config['region']})"
            )

        print()
        return 0

    # Print adapter information
    print_adapter_info(args.adapter)

    # Print activation checklist
    print_activation_checklist(args.adapter)

    # Print next steps
    print_next_steps(args.adapter)

    return 0


if __name__ == "__main__":
    sys.exit(main())
