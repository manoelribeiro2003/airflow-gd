"""Testes de integracao da carga atomica no Postgres via DuckDB.

Precisam de um Postgres real (a atomicidade depende da extensao postgres do
DuckDB), apontado por TEST_PG_URI. Sem a variavel, sao pulados. Exemplo:

    docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=pw \\
        -p 127.0.0.1:55439:5432 postgres:17-alpine
    TEST_PG_URI=postgresql://postgres:pw@127.0.0.1:55439/postgres \\
        uv run pytest tests/test_pg_load.py
"""

import os
import uuid

import duckdb as ddb
import pytest
from global_modules.pg_load import pg_transaction, replace_pg_table

PG_URI = os.environ.get("TEST_PG_URI")

pytestmark = pytest.mark.skipif(not PG_URI, reason="TEST_PG_URI nao definida")

# Falha no meio do INSERT: as primeiras linhas ja foram enviadas ao Postgres
# quando o erro estoura.
FAILING_SELECT = (
    "SELECT CASE WHEN range = 50000 THEN error('falha simulada') ELSE range END AS id "
    "FROM range(100000)"
)


def _attach(con: ddb.DuckDBPyConnection, read_only: bool = False) -> None:
    mode = ", READ_ONLY" if read_only else ""
    con.execute(f"ATTACH '{PG_URI}' AS pg (TYPE POSTGRES{mode})")


def _ids(table: str) -> list[int]:
    with ddb.connect() as con:
        _attach(con, read_only=True)
        return [r[0] for r in con.execute(f"SELECT id FROM pg.{table} ORDER BY id").fetchall()]


@pytest.fixture
def table():
    schema = f"test_pg_load_{uuid.uuid4().hex[:8]}"
    name = f"{schema}.alvo"
    with ddb.connect() as con:
        _attach(con)
        con.execute(
            f"CALL postgres_execute('pg', 'CREATE SCHEMA {schema}; "
            f"CREATE TABLE {name} (id int); INSERT INTO {name} VALUES (1), (2), (3)')"
        )
    yield name
    with ddb.connect() as con:
        _attach(con)
        con.execute(f"CALL postgres_execute('pg', 'DROP SCHEMA {schema} CASCADE')")


def test_replace_pg_table_troca_conteudo_e_retorna_linhas(table):
    with ddb.connect() as con:
        _attach(con)
        rows = replace_pg_table(con, table, "SELECT range AS id FROM range(10, 15)")

    expected = [10, 11, 12, 13, 14]
    assert rows == len(expected)
    assert _ids(table) == expected


def test_replace_pg_table_preserva_conteudo_anterior_em_falha(table):
    with ddb.connect() as con:
        _attach(con)
        with pytest.raises(ddb.Error, match="falha simulada"):
            replace_pg_table(con, table, FAILING_SELECT)

    assert _ids(table) == [1, 2, 3]


def test_replace_pg_table_pode_ser_repetida_apos_falha(table):
    with ddb.connect() as con:
        _attach(con)
        with pytest.raises(ddb.Error):
            replace_pg_table(con, table, FAILING_SELECT)
        rows = replace_pg_table(con, table, "SELECT 42 AS id")

    assert rows == 1
    assert _ids(table) == [42]


def _truncate_then_fail(con: ddb.DuckDBPyConnection, table: str) -> None:
    with pg_transaction(con):
        con.execute(f"CALL postgres_execute('pg', 'TRUNCATE TABLE {table}')")
        con.execute(f"INSERT INTO pg.{table} {FAILING_SELECT}")


def test_pg_transaction_desfaz_postgres_execute_em_falha(table):
    with ddb.connect() as con:
        _attach(con)
        with pytest.raises(ddb.Error, match="falha simulada"):
            _truncate_then_fail(con, table)

    assert _ids(table) == [1, 2, 3]


def test_pg_transaction_postgres_execute_enxerga_insert_da_mesma_transacao(table):
    """Padrao staging -> upsert: o comando via postgres_execute precisa ver as
    linhas que o DuckDB inseriu em pg.* antes do commit."""
    staging = f"{table}_stg"
    new_ids = [7, 8]
    with ddb.connect() as con:
        _attach(con)
        with pg_transaction(con):
            con.execute(f"CALL postgres_execute('pg', 'CREATE TABLE {staging} (id int)')")
            con.execute(f"INSERT INTO pg.{staging} SELECT unnest({new_ids}) AS id")
            (staged,) = con.execute(f"SELECT count(*) FROM pg.{staging}").fetchone() or (0,)
            con.execute(
                f"CALL postgres_execute('pg', 'INSERT INTO {table} SELECT id FROM {staging}')"
            )

    assert staged == len(new_ids)
    assert _ids(table) == [1, 2, 3, *new_ids]
