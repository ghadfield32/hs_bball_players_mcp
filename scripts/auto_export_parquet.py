"""
Auto-Export Parquet from DuckDB

Monitors DuckDB database and automatically exports updated data to Parquet files.
Can run as a standalone service or be invoked manually after data updates.

Usage:
    # Run once (export all current data):
    python scripts/auto_export_parquet.py --once

    # Run as a daemon (monitors and exports on interval):
    python scripts/auto_export_parquet.py --daemon --interval 3600

    # Export specific tables only:
    python scripts/auto_export_parquet.py --tables players,teams

    # Export with specific compression:
    python scripts/auto_export_parquet.py --compression snappy
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.services.duckdb_storage import get_duckdb_storage
from src.services.parquet_exporter import get_parquet_exporter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoExportService:
    """Service for automatic Parquet export from DuckDB."""

    def __init__(self):
        """Initialize auto-export service."""
        self.settings = get_settings()
        self.duckdb = get_duckdb_storage()
        self.exporter = get_parquet_exporter()
        self.last_export_time = {}
        logger.info("Auto-export service initialized")

    async def export_all_tables(self, compression: str = "snappy") -> dict:
        """
        Export all tables from DuckDB to Parquet.

        Args:
            compression: Compression algorithm (snappy, gzip, zstd, lz4)

        Returns:
            Dictionary with export results per table
        """
        results = {}

        # Table names in DuckDB
        tables = ["players", "teams", "player_season_stats", "games"]

        for table_name in tables:
            try:
                logger.info(f"Exporting table: {table_name}")

                # Query all data from table
                df = self.duckdb.conn.execute(f"SELECT * FROM {table_name}").df()

                if df.empty:
                    logger.info(f"Table {table_name} is empty, skipping export")
                    results[table_name] = {"status": "skipped", "reason": "empty"}
                    continue

                # Export to Parquet
                output_path = await self.exporter.export_to_parquet(
                    df=df, filename=f"{table_name}_full", compression=compression
                )

                logger.info(f"Exported {len(df)} rows from {table_name} to {output_path}")
                results[table_name] = {
                    "status": "success",
                    "rows": len(df),
                    "path": str(output_path),
                }

                # Update last export time
                self.last_export_time[table_name] = time.time()

            except Exception as e:
                logger.error(f"Failed to export table {table_name}", error=str(e))
                results[table_name] = {"status": "error", "error": str(e)}

        return results

    async def export_specific_tables(
        self, tables: list[str], compression: str = "snappy"
    ) -> dict:
        """
        Export specific tables from DuckDB to Parquet.

        Args:
            tables: List of table names to export
            compression: Compression algorithm

        Returns:
            Dictionary with export results per table
        """
        results = {}

        for table_name in tables:
            try:
                # Check if table exists
                table_check = self.duckdb.conn.execute(
                    f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
                ).fetchone()

                if not table_check or table_check[0] == 0:
                    logger.warning(f"Table {table_name} does not exist")
                    results[table_name] = {"status": "error", "error": "Table does not exist"}
                    continue

                # Query data
                df = self.duckdb.conn.execute(f"SELECT * FROM {table_name}").df()

                if df.empty:
                    logger.info(f"Table {table_name} is empty, skipping export")
                    results[table_name] = {"status": "skipped", "reason": "empty"}
                    continue

                # Export to Parquet
                output_path = await self.exporter.export_to_parquet(
                    df=df, filename=f"{table_name}_full", compression=compression
                )

                logger.info(f"Exported {len(df)} rows from {table_name} to {output_path}")
                results[table_name] = {
                    "status": "success",
                    "rows": len(df),
                    "path": str(output_path),
                }

                # Update last export time
                self.last_export_time[table_name] = time.time()

            except Exception as e:
                logger.error(f"Failed to export table {table_name}", error=str(e))
                results[table_name] = {"status": "error", "error": str(e)}

        return results

    async def run_daemon(self, interval: int = 3600, compression: str = "snappy"):
        """
        Run as a daemon, exporting at regular intervals.

        Args:
            interval: Seconds between exports
            compression: Compression algorithm
        """
        logger.info(f"Starting auto-export daemon (interval: {interval}s)")

        while True:
            try:
                logger.info("Running scheduled export")
                results = await self.export_all_tables(compression=compression)

                # Log summary
                success_count = sum(1 for r in results.values() if r.get("status") == "success")
                total_rows = sum(r.get("rows", 0) for r in results.values())

                logger.info(
                    f"Export completed: {success_count}/{len(results)} tables, {total_rows} total rows"
                )

                # Wait for next interval
                logger.info(f"Next export in {interval} seconds")
                await asyncio.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping daemon")
                break
            except Exception as e:
                logger.error("Error in daemon loop", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-export DuckDB data to Parquet files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export once:
  python scripts/auto_export_parquet.py --once

  # Run as daemon (every hour):
  python scripts/auto_export_parquet.py --daemon --interval 3600

  # Export specific tables:
  python scripts/auto_export_parquet.py --tables players,teams --once

  # Use different compression:
  python scripts/auto_export_parquet.py --once --compression zstd
        """,
    )

    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (default: daemon mode)"
    )

    parser.add_argument(
        "--daemon", action="store_true", help="Run as daemon with periodic exports"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between exports in daemon mode (default: 3600)",
    )

    parser.add_argument(
        "--tables", type=str, help="Comma-separated list of tables to export (default: all)"
    )

    parser.add_argument(
        "--compression",
        type=str,
        default="snappy",
        choices=["snappy", "gzip", "zstd", "lz4"],
        help="Compression algorithm (default: snappy)",
    )

    args = parser.parse_args()

    # Initialize service
    service = AutoExportService()

    # Determine mode
    if args.once:
        # Run once
        if args.tables:
            tables = [t.strip() for t in args.tables.split(",")]
            logger.info(f"Exporting specific tables: {tables}")
            results = await service.export_specific_tables(tables, compression=args.compression)
        else:
            logger.info("Exporting all tables")
            results = await service.export_all_tables(compression=args.compression)

        # Print summary
        print("\n" + "=" * 60)
        print("EXPORT SUMMARY")
        print("=" * 60)

        for table, result in results.items():
            status = result.get("status", "unknown")
            if status == "success":
                print(f"✓ {table}: {result['rows']} rows → {result['path']}")
            elif status == "skipped":
                print(f"⊘ {table}: skipped ({result['reason']})")
            else:
                print(f"✗ {table}: error - {result.get('error', 'unknown')}")

        print("=" * 60 + "\n")

    elif args.daemon:
        # Run as daemon
        await service.run_daemon(interval=args.interval, compression=args.compression)

    else:
        # Default: run once
        logger.info("No mode specified, running once (use --once or --daemon)")
        results = await service.export_all_tables(compression=args.compression)

        # Print summary
        print("\n" + "=" * 60)
        print("EXPORT SUMMARY")
        print("=" * 60)

        for table, result in results.items():
            status = result.get("status", "unknown")
            if status == "success":
                print(f"✓ {table}: {result['rows']} rows → {result['path']}")
            elif status == "skipped":
                print(f"⊘ {table}: skipped ({result['reason']})")
            else:
                print(f"✗ {table}: error - {result.get('error', 'unknown')}")

        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
