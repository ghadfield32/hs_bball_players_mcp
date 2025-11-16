"""Quick test to verify Bound data in DuckDB"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.duckdb_storage import get_duckdb_storage

storage = get_duckdb_storage()

# Check raw stats
result = storage.conn.execute(
    "SELECT player_name, season, points, points_per_game, games_played FROM player_season_stats WHERE source_type = 'bound' LIMIT 10"
).fetchall()

print("Raw Bound stats from DuckDB player_season_stats table:")
print("-" * 80)
for row in result:
    print(f"Player: {row[0]:<20} | Season: {row[1]} | Points: {row[2]:<6} | PPG: {row[3]:<6} | GP: {row[4]}")

# Check export function
import pandas as pd
df = storage.export_bound_from_duckdb()
print("\n" + "=" * 80)
print(f"Export function returned {len(df)} rows")
if not df.empty:
    print("\nFirst 5 rows from export_bound_from_duckdb():")
    print(df[['player_name', 'pts_per_g', 'reb_per_g', 'school_state']].head())
