"""
Schema Loader Utility

Loads YAML schemas and converts to DuckDB DDL.

Author: Claude Code
Date: 2025-11-15
"""

from pathlib import Path
from typing import Dict, List
import yaml


def load_schema(schema_name: str) -> Dict:
    """
    Load a YAML schema file.

    Args:
        schema_name: Name of schema file without .yaml extension

    Returns:
        Dict with schema definition
    """
    schema_path = Path(__file__).parent.parent.parent / "schemas" / f"{schema_name}.yaml"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, 'r') as f:
        return yaml.safe_load(f)


def yaml_type_to_duckdb_type(yaml_type: str) -> str:
    """
    Convert YAML type to DuckDB SQL type.

    Args:
        yaml_type: Type from YAML schema

    Returns:
        DuckDB SQL type string
    """
    type_map = {
        "VARCHAR": "VARCHAR",
        "INTEGER": "INTEGER",
        "INT": "INTEGER",
        "DOUBLE": "DOUBLE",
        "FLOAT": "DOUBLE",
        "BOOLEAN": "BOOLEAN",
        "TIMESTAMP": "TIMESTAMP",
        "DATE": "DATE",
        "JSON": "JSON",
    }

    return type_map.get(yaml_type.upper(), "VARCHAR")


def generate_ddl_from_yaml(schema_name: str) -> str:
    """
    Generate DuckDB DDL from YAML schema.

    Args:
        schema_name: Name of schema file without .yaml

    Returns:
        SQL CREATE TABLE statement

    Example:
        ddl = generate_ddl_from_yaml("player_recruiting")
        conn.execute(ddl)
    """
    schema = load_schema(schema_name)

    table_name = schema['table_name']
    columns = schema['columns']

    # Start DDL
    ddl_parts = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]

    # Add columns
    column_defs = []
    for col_name, col_spec in columns.items():
        col_type = yaml_type_to_duckdb_type(col_spec['type'])
        nullable = "" if col_spec.get('nullable', True) else " NOT NULL"
        primary_key = " PRIMARY KEY" if col_spec.get('primary_key', False) else ""

        column_defs.append(f"    {col_name} {col_type}{nullable}{primary_key}")

    ddl_parts.append(",\n".join(column_defs))
    ddl_parts.append(")")

    ddl = "\n".join(ddl_parts)

    # Add indexes
    index_ddls = []
    if 'indexes' in schema:
        for idx in schema['indexes']:
            idx_name = idx['name']
            idx_cols = ", ".join(idx['columns'])
            unique = "UNIQUE " if idx.get('unique', False) else ""

            index_ddl = f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} ON {table_name}({idx_cols})"
            index_ddls.append(index_ddl)

    return ddl, index_ddls


def generate_all_recruiting_ddl() -> List[str]:
    """
    Generate DDL for all recruiting schemas.

    Returns:
        List of SQL statements to execute
    """
    schemas = [
        "on3_player_rankings_raw",
        "player_recruiting",
        "recruiting_coverage"
    ]

    all_ddls = []

    for schema_name in schemas:
        table_ddl, index_ddls = generate_ddl_from_yaml(schema_name)
        all_ddls.append(table_ddl)
        all_ddls.extend(index_ddls)

    return all_ddls
