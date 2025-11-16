"""
Data Inventory Report Script

Generates comprehensive status report of all datasets:
- What datasets exist
- How far back they go (date ranges)
- How current they are (latest retrieval timestamp)
- What we're getting for each (player counts, fields)

Usage:
    python scripts/data_inventory.py
    python scripts/data_inventory.py --output data_inventory.json

Author: Claude Code
Date: 2025-11-15
Phase: 15 - Data Inventory
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DataInventory:
    """
    Generates comprehensive inventory of all basketball data sources.
    """

    def __init__(self):
        """Initialize data inventory."""
        self.inventory = {
            'generated_at': datetime.now().isoformat(),
            'datasets': {},
            'summary': {}
        }
        self.duckdb_storage = None

    def initialize_duckdb(self):
        """Initialize DuckDB connection."""
        try:
            # Direct DuckDB connection to avoid circular imports
            import duckdb
            from pathlib import Path

            # Use the actual DuckDB path from config (data/analytics.duckdb)
            db_path = Path("data/analytics.duckdb")
            db_path.parent.mkdir(parents=True, exist_ok=True)

            class DuckDBWrapper:
                def __init__(self, path):
                    self.conn = duckdb.connect(str(path))

            self.duckdb_storage = DuckDBWrapper(db_path)
            print("[OK] DuckDB connection initialized")
        except Exception as e:
            print(f"[WARNING] DuckDB connection failed: {e}")
            self.duckdb_storage = None

    def check_parquet_files(self) -> Dict[str, Any]:
        """Check all Parquet files in data/ directory."""
        parquet_files = {}
        data_dir = Path("data")

        if not data_dir.exists():
            return parquet_files

        # Find all Parquet files recursively
        for parquet_file in data_dir.rglob("*.parquet"):
            try:
                df = pd.read_parquet(parquet_file)

                # Extract metadata
                file_info = {
                    'path': str(parquet_file),
                    'size_mb': parquet_file.stat().st_size / (1024 * 1024),
                    'row_count': len(df),
                    'columns': df.columns.tolist(),
                    'date_created': datetime.fromtimestamp(parquet_file.stat().st_mtime).isoformat(),
                }

                # Try to extract date ranges
                if 'retrieved_at' in df.columns:
                    file_info['earliest_retrieval'] = str(df['retrieved_at'].min())
                    file_info['latest_retrieval'] = str(df['retrieved_at'].max())

                if 'season' in df.columns:
                    file_info['seasons'] = sorted(df['season'].unique().tolist())

                if 'class_year' in df.columns:
                    file_info['class_years'] = sorted(df['class_year'].unique().tolist())

                if 'grad_year' in df.columns:
                    file_info['grad_years'] = sorted(df['grad_year'].unique().tolist())

                # Add sample data preview
                file_info['sample_preview'] = df.head(3).to_dict('records')

                parquet_files[parquet_file.stem] = file_info

            except Exception as e:
                print(f"[WARNING] Error reading {parquet_file}: {e}")
                parquet_files[parquet_file.stem] = {
                    'path': str(parquet_file),
                    'error': str(e)
                }

        return parquet_files

    def check_duckdb_tables(self) -> Dict[str, Any]:
        """Check all DuckDB tables."""
        if not self.duckdb_storage:
            return {'error': 'DuckDB not initialized'}

        tables_info = {}

        try:
            # Get list of all tables
            tables_result = self.duckdb_storage.conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
            """).fetchall()

            tables = [row[0] for row in tables_result]

            for table in tables:
                try:
                    # Get row count
                    count_result = self.duckdb_storage.conn.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()
                    row_count = count_result[0] if count_result else 0

                    # Get column info
                    columns_result = self.duckdb_storage.conn.execute(f"""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = '{table}'
                    """).fetchall()

                    columns = {col[0]: col[1] for col in columns_result}

                    # Get sample data
                    sample_result = self.duckdb_storage.conn.execute(
                        f"SELECT * FROM {table} LIMIT 3"
                    ).fetchdf()

                    # Try to get date ranges
                    date_info = {}
                    if 'retrieved_at' in columns:
                        date_range = self.duckdb_storage.conn.execute(f"""
                            SELECT MIN(retrieved_at) as earliest, MAX(retrieved_at) as latest
                            FROM {table}
                        """).fetchone()
                        if date_range:
                            date_info['earliest_retrieval'] = str(date_range[0])
                            date_info['latest_retrieval'] = str(date_range[1])

                    if 'season' in columns:
                        seasons = self.duckdb_storage.conn.execute(f"""
                            SELECT DISTINCT season FROM {table} ORDER BY season
                        """).fetchall()
                        date_info['seasons'] = [s[0] for s in seasons]

                    if 'class_year' in columns:
                        years = self.duckdb_storage.conn.execute(f"""
                            SELECT DISTINCT class_year FROM {table} ORDER BY class_year
                        """).fetchall()
                        date_info['class_years'] = [y[0] for y in years]

                    tables_info[table] = {
                        'row_count': row_count,
                        'columns': list(columns.keys()),
                        'column_types': columns,
                        **date_info,
                        'sample_data': sample_result.head(3).to_dict('records')
                    }

                except Exception as e:
                    print(f"[WARNING] Error reading table {table}: {e}")
                    tables_info[table] = {'error': str(e)}

        except Exception as e:
            print(f"[WARNING] Error querying DuckDB: {e}")
            return {'error': str(e)}

        return tables_info

    def generate_summary(self, parquet_info: Dict, duckdb_info: Dict) -> Dict[str, Any]:
        """Generate overall summary statistics."""
        summary = {
            'parquet_files_count': len([f for f in parquet_info.values() if 'error' not in f]),
            'parquet_total_rows': sum(f.get('row_count', 0) for f in parquet_info.values() if 'error' not in f),
            'parquet_total_size_mb': sum(f.get('size_mb', 0) for f in parquet_info.values() if 'error' not in f),
            'duckdb_tables_count': len([t for t in duckdb_info.values() if 'error' not in t]),
            'duckdb_total_rows': sum(t.get('row_count', 0) for t in duckdb_info.values() if 'error' not in t),
        }

        # Data source status
        summary['data_sources'] = {
            'eybl': {
                'parquet': 'player_season_stats' in parquet_info,
                'duckdb': 'player_season_stats' in duckdb_info,
                'row_count': duckdb_info.get('player_season_stats', {}).get('row_count', 0)
            },
            'recruiting': {
                'parquet': 'recruiting_ranks' in parquet_info,
                'duckdb': 'recruiting_ranks' in duckdb_info,
                'row_count': duckdb_info.get('recruiting_ranks', {}).get('row_count', 0)
            },
            'maxpreps': {
                'parquet': False,  # Will be updated when MaxPreps data is fetched
                'duckdb': False,
                'row_count': 0
            },
            'college_offers': {
                'parquet': False,
                'duckdb': 'college_offers' in duckdb_info,
                'row_count': duckdb_info.get('college_offers', {}).get('row_count', 0)
            }
        }

        return summary

    def run(self) -> Dict[str, Any]:
        """Run full data inventory."""
        print("=" * 60)
        print("Data Inventory Report")
        print("=" * 60)
        print()

        # Initialize DuckDB
        self.initialize_duckdb()

        # Check Parquet files
        print("[1/3] Scanning Parquet files...")
        parquet_info = self.check_parquet_files()
        print(f"   Found {len(parquet_info)} Parquet file(s)")

        # Check DuckDB tables
        print("[2/3] Scanning DuckDB tables...")
        duckdb_info = self.check_duckdb_tables()
        if 'error' not in duckdb_info:
            print(f"   Found {len(duckdb_info)} table(s)")
        else:
            print(f"   [WARNING] Error: {duckdb_info['error']}")

        # Generate summary
        print("[3/3] Generating summary...")
        summary = self.generate_summary(parquet_info, duckdb_info)

        # Assemble full inventory
        self.inventory['datasets']['parquet'] = parquet_info
        self.inventory['datasets']['duckdb'] = duckdb_info
        self.inventory['summary'] = summary

        print("[OK] Inventory complete")
        print()

        return self.inventory

    def print_report(self):
        """Print human-readable report to console."""
        print("=" * 60)
        print("DATA INVENTORY SUMMARY")
        print("=" * 60)
        print(f"Generated: {self.inventory['generated_at']}")
        print()

        # Summary stats
        summary = self.inventory['summary']
        print("OVERALL STATISTICS:")
        print(f"   Parquet files: {summary['parquet_files_count']} ({summary['parquet_total_size_mb']:.2f} MB)")
        print(f"   Total Parquet rows: {summary['parquet_total_rows']:,}")
        print(f"   DuckDB tables: {summary['duckdb_tables_count']}")
        print(f"   Total DuckDB rows: {summary['duckdb_total_rows']:,}")
        print()

        # Data source status
        print("DATA SOURCE STATUS:")
        for source, status in summary['data_sources'].items():
            parquet_status = "[YES]" if status['parquet'] else "[NO]"
            duckdb_status = "[YES]" if status['duckdb'] else "[NO]"
            print(f"   {source.upper():20} Parquet: {parquet_status}  DuckDB: {duckdb_status}  Rows: {status['row_count']:,}")
        print()

        # Detailed table info
        print("DUCKDB TABLES DETAIL:")
        duckdb_info = self.inventory['datasets']['duckdb']
        if 'error' not in duckdb_info:
            for table_name, table_info in duckdb_info.items():
                if 'error' not in table_info:
                    print(f"   {table_name}:")
                    print(f"      Rows: {table_info['row_count']:,}")
                    print(f"      Columns: {len(table_info['columns'])}")

                    if 'seasons' in table_info:
                        print(f"      Seasons: {', '.join(map(str, table_info['seasons']))}")
                    if 'class_years' in table_info:
                        print(f"      Class Years: {', '.join(map(str, table_info['class_years']))}")
                    if 'earliest_retrieval' in table_info:
                        print(f"      Data Range: {table_info['earliest_retrieval']} to {table_info['latest_retrieval']}")
                    print()
        else:
            print(f"   [WARNING] Error: {duckdb_info['error']}")

        # Parquet files detail
        print("PARQUET FILES DETAIL:")
        parquet_info = self.inventory['datasets']['parquet']
        for file_name, file_info in parquet_info.items():
            if 'error' not in file_info:
                print(f"   {file_name}:")
                print(f"      Path: {file_info['path']}")
                print(f"      Size: {file_info['size_mb']:.2f} MB")
                print(f"      Rows: {file_info['row_count']:,}")
                print(f"      Columns: {len(file_info['columns'])}")

                if 'seasons' in file_info:
                    print(f"      Seasons: {', '.join(map(str, file_info['seasons']))}")
                if 'class_years' in file_info:
                    print(f"      Class Years: {', '.join(map(str, file_info['class_years']))}")
                print()

        print("=" * 60)

    def save_to_json(self, output_path: str):
        """Save inventory to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(self.inventory, f, indent=2, default=str)

        print(f"[SAVED] Inventory saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate data inventory report")

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output JSON file path (optional)'
    )

    args = parser.parse_args()

    # Create inventory
    inventory = DataInventory()
    inventory.run()

    # Print report
    inventory.print_report()

    # Save to JSON if requested
    if args.output:
        inventory.save_to_json(args.output)


if __name__ == '__main__':
    main()
