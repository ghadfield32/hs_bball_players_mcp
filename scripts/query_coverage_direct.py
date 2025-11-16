"""Direct DuckDB query for coverage data."""

import duckdb

conn = duckdb.connect("data/duckdb/recruiting.duckdb")

print("\n" + "=" * 80)
print("RECRUITING COVERAGE DATA")
print("=" * 80 + "\n")

df = conn.execute("""
    SELECT
        source,
        class_year,
        n_players,
        n_players_with_ranks,
        n_players_with_stars,
        n_players_committed,
        notes
    FROM recruiting_coverage
    ORDER BY source, class_year
""").df()

if df.empty:
    print("No coverage data found")
else:
    print(df.to_string(index=False))

conn.close()
print()
