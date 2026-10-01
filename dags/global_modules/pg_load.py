"""Carga atomica no Postgres a partir de uma conexao DuckDB com o PG anexado como `pg`.

`postgres_execute` e escritas em `pg.*` rodam na mesma transacao Postgres da
transacao DuckDB aberta. Fora dela, cada chamada commita sozinha: um TRUNCATE
seguido de um INSERT que falha deixaria a tabela vazia.
"""

from collections.abc import Generator
from contextlib import contextmanager, suppress

import duckdb as ddb


@contextmanager
def pg_transaction(con: ddb.DuckDBPyConnection) -> Generator[None]:
    """Agrupa os comandos do bloco numa unica transacao; desfaz tudo em falha."""
    con.begin()
    try:
        yield
    except BaseException:
        # rollback que falha (ex.: conexao caiu) nao pode esconder o erro original;
        # o Postgres desfaz a transacao sozinho quando a conexao fecha.
        with suppress(ddb.Error):
            con.rollback()
        raise
    con.commit()


def replace_pg_table(con: ddb.DuckDBPyConnection, table: str, select_sql: str) -> int:
    """Substitui o conteudo de `table` pelo resultado de `select_sql` numa unica
    transacao. Em falha, a tabela mantem o conteudo anterior e a chamada pode
    ser repetida. Leitores concorrentes aguardam o lock do TRUNCATE ate o commit.

    Retorna o numero de linhas carregadas."""
    with pg_transaction(con):
        con.execute(f"CALL postgres_execute('pg', 'TRUNCATE TABLE {table}')")
        row = con.execute(f"INSERT INTO pg.{table} {select_sql}").fetchone()
    return row[0] if row else 0
