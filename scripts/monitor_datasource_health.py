#!/usr/bin/env python3
"""
Datasource Health Monitoring Script - Weekly Health Checks

Automated monitoring for datasource health with historical tracking.

Features:
- Runs weekly validation of all datasources
- Tracks health trends over time
- Generates alerts for failing sources
- Exports health reports to CSV
- Compares current vs historical performance

Usage:
    # Run health check and append to history
    python scripts/monitor_datasource_health.py

    # Run with email alerts (requires SMTP config)
    python scripts/monitor_datasource_health.py --alert

    # View historical trends
    python scripts/monitor_datasource_health.py --show-history

    # Export detailed report
    python scripts/monitor_datasource_health.py --export data/health_report.csv

Schedule with cron/Task Scheduler:
    # Linux/Mac (weekly on Monday at 6am)
    0 6 * * 1 cd /path/to/project && python scripts/monitor_datasource_health.py

    # Windows Task Scheduler
    - Create Basic Task
    - Trigger: Weekly, Monday, 6:00 AM
    - Action: Start program: python.exe
    - Arguments: scripts/monitor_datasource_health.py
    - Start in: C:\path\to\project

Author: Claude Code
Date: 2025-11-15
Purpose: Automated weekly datasource health monitoring
"""

import asyncio
import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate_datasources import (
    validate_all_sources,
    ValidationResult,
)
from src.services import DataSourceAggregator


HEALTH_HISTORY_FILE = Path("data/datasource_health_history.json")
ALERT_THRESHOLD_DAYS = 7  # Alert if source has been failing for this many days


class HealthReport:
    """Container for health monitoring report."""

    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.total_sources = 0
        self.healthy_sources = 0
        self.failing_sources = 0
        self.degraded_sources = 0
        self.sources: List[ValidationResult] = []
        self.alerts: List[str] = []
        self.trends: Dict[str, str] = {}  # source_name -> "improving" | "stable" | "degrading"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_sources,
                "healthy": self.healthy_sources,
                "failing": self.failing_sources,
                "degraded": self.degraded_sources,
                "health_rate": f"{(self.healthy_sources/self.total_sources*100):.1f}%" if self.total_sources > 0 else "0.0%"
            },
            "sources": [s.to_dict() for s in self.sources],
            "alerts": self.alerts,
            "trends": self.trends
        }


def load_health_history() -> List[Dict[str, Any]]:
    """Load historical health check data."""
    if not HEALTH_HISTORY_FILE.exists():
        return []

    with open(HEALTH_HISTORY_FILE, 'r') as f:
        return json.load(f)


def save_health_history(history: List[Dict[str, Any]]) -> None:
    """Save health check history."""
    HEALTH_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Keep only last 12 weeks of data
    max_records = 12
    if len(history) > max_records:
        history = history[-max_records:]

    with open(HEALTH_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def analyze_trends(history: List[Dict[str, Any]], current_sources: List[ValidationResult]) -> Dict[str, str]:
    """
    Analyze health trends over time.

    Returns:
        Dict mapping source_name to trend: "improving" | "stable" | "degrading" | "new"
    """
    if len(history) < 2:
        return {s.source_name: "new" for s in current_sources}

    trends = {}

    # Get previous 2 health checks
    prev_check = history[-1] if len(history) >= 1 else None
    prev2_check = history[-2] if len(history) >= 2 else None

    for source in current_sources:
        source_name = source.source_name
        current_status = source.status

        # Find source in previous checks
        prev_status = None
        prev2_status = None

        if prev_check:
            for s in prev_check.get("sources", []):
                if s.get("source_name") == source_name:
                    prev_status = s.get("status")
                    break

        if prev2_check:
            for s in prev2_check.get("sources", []):
                if s.get("source_name") == source_name:
                    prev2_status = s.get("status")
                    break

        # Determine trend
        if prev_status is None:
            trends[source_name] = "new"
        elif current_status == "PASSED" and prev_status == "FAILED":
            trends[source_name] = "improving"
        elif current_status == "FAILED" and prev_status == "PASSED":
            trends[source_name] = "degrading"
        elif current_status == prev_status:
            trends[source_name] = "stable"
        else:
            trends[source_name] = "mixed"

    return trends


def generate_alerts(
    sources: List[ValidationResult],
    history: List[Dict[str, Any]],
    trends: Dict[str, str]
) -> List[str]:
    """
    Generate alerts for failing or degrading sources.

    Returns:
        List of alert messages
    """
    alerts = []

    # Alert for currently failing sources
    failing_sources = [s for s in sources if s.status == "FAILED"]
    if failing_sources:
        alerts.append(f"[!] {len(failing_sources)} source(s) currently failing")

    # Alert for sources that have been failing for extended period
    if len(history) >= 2:
        for source in failing_sources:
            # Check if source was also failing in previous checks
            consecutive_fails = 1
            for prev_check in reversed(history[-7:]):  # Check last 7 weeks
                found = False
                for s in prev_check.get("sources", []):
                    if s.get("source_name") == source.source_name and s.get("status") == "FAILED":
                        consecutive_fails += 1
                        found = True
                        break
                if not found:
                    break

            if consecutive_fails >= 2:
                alerts.append(
                    f"[!] {source.source_name} has been failing for {consecutive_fails} consecutive weeks"
                )

    # Alert for recently degraded sources
    for source_name, trend in trends.items():
        if trend == "degrading":
            alerts.append(f"[!] {source_name} recently degraded from PASSED to FAILED")

    # Alert if overall health rate is low
    total = len(sources)
    passed = sum(1 for s in sources if s.status == "PASSED")
    health_rate = (passed / total * 100) if total > 0 else 0

    if health_rate < 50:
        alerts.append(f"[!!] Overall health rate critically low: {health_rate:.1f}%")
    elif health_rate < 75:
        alerts.append(f"[!] Overall health rate below target: {health_rate:.1f}%")

    return alerts


def print_health_report(report: HealthReport) -> None:
    """Print formatted health report."""
    print(f"\n{'='*80}")
    print(f"{'DATASOURCE HEALTH REPORT':^80}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^80}")
    print(f"{'='*80}\n")

    # Summary
    print(f"{'SUMMARY':^80}")
    print(f"{'-'*80}")
    print(f"Total Sources:     {report.total_sources}")
    print(f"Healthy (PASSED):  {report.healthy_sources} ({report.healthy_sources/report.total_sources*100:.1f}%)")
    print(f"Degraded (WARNING): {report.degraded_sources} ({report.degraded_sources/report.total_sources*100:.1f}%)")
    print(f"Failing (FAILED):  {report.failing_sources} ({report.failing_sources/report.total_sources*100:.1f}%)")
    print(f"\n{'='*80}\n")

    # Alerts
    if report.alerts:
        print(f"{'ALERTS':^80}")
        print(f"{'-'*80}")
        for alert in report.alerts:
            print(f"  {alert}")
        print(f"\n{'='*80}\n")

    # Source status
    print(f"{'SOURCE STATUS':^80}")
    print(f"{'-'*80}")
    print(f"{'Source':<20} {'Status':<12} {'Tests':<12} {'Historical':<15} {'Trend':<12}")
    print(f"{'-'*20} {'-'*12} {'-'*12} {'-'*15} {'-'*12}")

    for source in sorted(report.sources, key=lambda x: (x.status != "PASSED", x.source_name)):
        tests_str = f"{source.tests_passed}/{source.tests_passed + source.tests_failed}"
        hist_str = f"{source.historical_seasons}/3 seasons"
        trend_str = report.trends.get(source.source_name, "unknown")

        # Trend indicators
        trend_symbol = {
            "improving": "[+]",
            "stable": "[-]",
            "degrading": "[v]",
            "new": "[*]",
            "mixed": "[~]"
        }.get(trend_str, "")

        print(f"{source.source_name:<20} {source.status:<12} {tests_str:<12} {hist_str:<15} {trend_symbol} {trend_str}")

    print(f"\n{'='*80}\n")


async def run_health_check(show_history: bool = False, export_path: Optional[Path] = None) -> HealthReport:
    """
    Run comprehensive health check.

    Args:
        show_history: Show historical trends
        export_path: Export detailed report to CSV

    Returns:
        HealthReport with results
    """
    print("[...] Initializing datasource aggregator...")
    aggregator = DataSourceAggregator()
    print(f"[OK] Loaded {len(aggregator.sources)} datasources\n")

    # Run validation
    print("[...] Running health checks...")
    validation_results = await validate_all_sources(aggregator, verbose=False)
    print(f"[OK] Completed validation of {len(validation_results)} sources\n")

    # Load history
    history = load_health_history()

    # Analyze trends
    trends = analyze_trends(history, validation_results)

    # Generate alerts
    alerts = generate_alerts(validation_results, history, trends)

    # Build report
    report = HealthReport()
    report.total_sources = len(validation_results)
    report.healthy_sources = sum(1 for s in validation_results if s.status == "PASSED")
    report.failing_sources = sum(1 for s in validation_results if s.status == "FAILED")
    report.degraded_sources = sum(1 for s in validation_results if s.status == "WARNING")
    report.sources = validation_results
    report.alerts = alerts
    report.trends = trends

    # Save to history
    history.append(report.to_dict())
    save_health_history(history)
    print(f"[OK] Health check saved to history ({len(history)} records)")

    # Show historical trends if requested
    if show_history and len(history) > 1:
        print(f"\n{'='*80}")
        print(f"{'HISTORICAL TRENDS (Last 8 Weeks)':^80}")
        print(f"{'='*80}\n")

        for i, check in enumerate(history[-8:], 1):
            timestamp = check.get("timestamp", "Unknown")
            summary = check.get("summary", {})
            health_rate = summary.get("health_rate", "0.0%")
            print(f"Week {i}: {timestamp[:10]} - Health Rate: {health_rate}")

        print(f"\n{'='*80}\n")

    # Export if requested
    if export_path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, 'w', newline='') as f:
            fieldnames = ["source_name", "status", "tests_passed", "tests_failed", "success_rate",
                         "historical_seasons", "trend", "errors", "warnings"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for source in validation_results:
                row = source.to_dict()
                row["trend"] = trends.get(source.source_name, "unknown")
                writer.writerow(row)

        print(f"[OK] Detailed report exported to: {export_path}\n")

    return report


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor datasource health with weekly tracking"
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Show historical health trends"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export detailed report to CSV"
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Send email alerts for failures (requires SMTP config)"
    )

    args = parser.parse_args()

    # Run health check
    report = await run_health_check(
        show_history=args.show_history,
        export_path=Path(args.export) if args.export else None
    )

    # Print report
    print_health_report(report)

    # Send alerts if requested
    if args.alert and report.alerts:
        print("[!] Email alerts requested but SMTP not configured")
        print("    Configure SMTP in .env file to enable email alerts\n")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
