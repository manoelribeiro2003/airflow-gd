from __future__ import annotations

import re
from pathlib import Path

import duckdb
from airflow.utils.log.logging_mixin import LoggingMixin
from sqlalchemy import types as sa_types

log = LoggingMixin().log

_IDENT_SAFE = re.compile(r"^\w+$")


def quote_ident(name: str) -> str:
    if not _IDENT_SAFE.match(name):
        raise ValueError(f"Identificador de coluna inválido: {name!r}")
    return f'"{name}"'


def sa_type_to_duckdb(col_type: sa_types.TypeEngine | type) -> str:  # noqa: PLR0911
    if isinstance(col_type, type):
        col_type = col_type()

    if isinstance(col_type, sa_types.Boolean):
        return "BOOLEAN"
    if isinstance(col_type, sa_types.Integer):
        return "INTEGER"
    # Float deve ser checado antes de Numeric — Float é subclasse de Numeric no SQLAlchemy
    if isinstance(col_type, sa_types.Float):
        return "DOUBLE"
    if isinstance(col_type, sa_types.Numeric):
        p = col_type.precision or 18
        s = col_type.scale or 2
        return f"DECIMAL({p}, {s})"
    if isinstance(col_type, sa_types.DateTime):
        return "TIMESTAMPTZ" if col_type.timezone else "TIMESTAMP"
    if isinstance(col_type, sa_types.Date):
        return "DATE"
    if isinstance(col_type, sa_types.String):
        length = col_type.length
        return f"VARCHAR({length})" if length else "VARCHAR"
    raise ValueError(f"Tipo 'sqlalchemy.types' não suportado: {type(col_type).__name__}")


def build_select_with_cast(
    parquet_path: str | Path,
    schema: dict[str, sa_types.TypeEngine],
) -> str:
    parquet_path = Path(parquet_path)
    path_str = parquet_path.as_posix()
    if "'" in path_str:
        raise ValueError(f"Caminho do parquet contém aspas simples: {path_str!r}")

    with duckdb.connect() as con:
        rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path_str}')").fetchall()
    parquet_cols = {row[0] for row in rows}

    parts = []
    for col, col_type in schema.items():
        if col not in parquet_cols:
            log.debug("[CAST] Coluna '%s' ausente no parquet, ignorando", col)
            continue
        duckdb_type = sa_type_to_duckdb(col_type)
        parts.append(f"CAST({quote_ident(col)} AS {duckdb_type}) AS {quote_ident(col)}")

    if not parts:
        raise ValueError("Nenhuma coluna do schema encontrada no parquet")

    return f"SELECT {', '.join(parts)} FROM read_parquet('{path_str}')"
