"""Quick script to query coverage data from DuckDB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.recruiting_duckdb import RecruitingDuckDBStorage

storage = RecruitingDuckDBStorage()

print("\n" + "=" * 70)
print("RECRUITING COVERAGE DATA")
print("=" * 70)

df = storage.get_coverage()

if df.empty:
    print("No coverage data found")
else:
    print(df[["source", "class_year", "n_players", "n_players_with_ranks", "n_players_committed", "notes"]].to_string(index=False))

storage.close()
print()
