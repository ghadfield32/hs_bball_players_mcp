#!/usr/bin/env python3
"""
Comprehensive Datasource Inventory Analysis

Analyzes all datasources in the repository to document:
1. What each datasource provides (stats, teams, schedules, etc.)
2. Historical data availability
3. Current operational status
4. Data quality and completeness
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Any


def analyze_datasource_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze a datasource file to extract key information.

    Returns dict with:
    - name: Datasource name
    - category: US State, Grassroots, Recruiting, International, etc.
    - methods: Available methods (search_players, get_player_stats, etc.)
    - base_url: Website URL
    - notes: Any special notes from docstrings
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        info = {
            'file': file_path.name,
            'path': str(file_path),
            'category': _categorize_datasource(file_path),
            'class_name': None,
            'methods': [],
            'base_url': None,
            'notes': [],
        }

        # Find the main datasource class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Look for DataSource classes
                if 'DataSource' in node.name or 'Source' in node.name:
                    info['class_name'] = node.name

                    # Get class docstring
                    docstring = ast.get_docstring(node)
                    if docstring:
                        # Extract first line as note
                        first_line = docstring.split('\n')[0].strip()
                        if first_line:
                            info['notes'].append(first_line)

                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Skip private methods
                            if not item.name.startswith('_'):
                                info['methods'].append(item.name)

            # Look for base_url assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and 'url' in target.id.lower():
                        if isinstance(node.value, ast.Constant):
                            if isinstance(node.value.value, str) and node.value.value.startswith('http'):
                                info['base_url'] = node.value.value
                                break

        return info

    except Exception as e:
        return {
            'file': file_path.name,
            'path': str(file_path),
            'error': str(e)
        }


def _categorize_datasource(file_path: Path) -> str:
    """Categorize datasource by path."""
    path_str = str(file_path)

    if 'recruiting' in path_str:
        return 'Recruiting'
    elif 'europe' in path_str:
        return 'Europe'
    elif 'australia' in path_str:
        return 'Australia'
    elif 'canada' in path_str:
        return 'Canada'
    elif 'global' in path_str:
        return 'Global'
    elif 'us/state' in path_str:
        return 'US State Template'
    elif 'us/' in path_str:
        # Check if it's a grassroots circuit or state association
        name_lower = file_path.stem.lower()
        grassroots = ['eybl', 'uaa', '3ssb', 'three_ssb', 'grind', 'ote', 'bound',
                      'nepsac', 'wsn', 'sblive', 'rankone']

        if any(circuit in name_lower for circuit in grassroots):
            return 'US Grassroots/Elite'
        elif 'maxpreps' in name_lower:
            return 'US National'
        elif name_lower == 'psal' or name_lower == 'mn_hub':
            return 'US Regional'
        else:
            # State associations
            return 'US State Association'

    return 'Other'


def main():
    """Analyze all datasources and generate comprehensive inventory."""

    datasources_dir = Path('src/datasources')

    # Find all Python files
    all_files = list(datasources_dir.rglob('*.py'))

    # Filter out __init__.py, base.py, and archive
    datasource_files = [
        f for f in all_files
        if f.name not in ['__init__.py', 'base.py', 'base_association.py', 'base_recruiting.py']
        and 'archive' not in str(f)
        and 'enhanced_parser' not in str(f)
    ]

    print(f"[INFO] Analyzing {len(datasource_files)} datasource files...\n")

    # Analyze each file
    results = []
    for file_path in sorted(datasource_files):
        info = analyze_datasource_file(file_path)
        results.append(info)

    # Group by category
    by_category = {}
    for result in results:
        category = result.get('category', 'Other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(result)

    # Print organized report
    print("=" * 100)
    print("DATASOURCE INVENTORY - COMPREHENSIVE OVERVIEW")
    print("=" * 100)
    print()

    # Summary stats
    print("SUMMARY STATISTICS:")
    print(f"  Total Datasources: {len(results)}")
    print(f"  Categories: {len(by_category)}")
    print()

    for category in sorted(by_category.keys()):
        count = len(by_category[category])
        print(f"  {category}: {count} datasources")
    print()

    # Detailed breakdown by category
    print("=" * 100)
    print("DETAILED BREAKDOWN BY CATEGORY")
    print("=" * 100)
    print()

    for category in sorted(by_category.keys()):
        sources = by_category[category]

        print(f"\n{'=' * 100}")
        print(f"{category.upper()} ({len(sources)} sources)")
        print(f"{'=' * 100}\n")

        for source in sorted(sources, key=lambda x: x['file']):
            print(f"  [{source['file']}]")

            if source.get('class_name'):
                print(f"    Class: {source['class_name']}")

            if source.get('base_url'):
                print(f"    URL:   {source['base_url'][:80]}")

            if source.get('methods'):
                # Key methods
                key_methods = [m for m in source['methods'] if m in [
                    'search_players', 'get_player_stats', 'get_player_season_stats',
                    'get_teams', 'get_schedule', 'get_leaderboard', 'get_game_stats',
                    'get_rankings', 'get_player_recruiting_profile'
                ]]

                if key_methods:
                    print(f"    Methods: {', '.join(key_methods)}")

            if source.get('notes'):
                note = source['notes'][0]
                if len(note) > 80:
                    note = note[:77] + "..."
                print(f"    Notes: {note}")

            if source.get('error'):
                print(f"    ERROR: {source['error']}")

            print()

    # Generate method availability matrix
    print("\n" + "=" * 100)
    print("METHOD AVAILABILITY MATRIX")
    print("=" * 100)
    print()

    method_names = [
        'search_players', 'get_player_stats', 'get_player_season_stats',
        'get_teams', 'get_schedule', 'get_leaderboard', 'get_game_stats'
    ]

    for category in sorted(by_category.keys()):
        sources = by_category[category]

        # Count method availability
        method_counts = {method: 0 for method in method_names}
        for source in sources:
            methods = source.get('methods', [])
            for method in method_names:
                if method in methods:
                    method_counts[method] += 1

        print(f"\n{category}:")
        for method, count in method_counts.items():
            pct = (count / len(sources) * 100) if sources else 0
            print(f"  {method:30} {count:3}/{len(sources):3} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
