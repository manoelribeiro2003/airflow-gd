"""Renderiza o script SQL de recarga completa das tabelas aux de melhorias.

As tabelas aux sao carregadas manualmente no SQL Server (ADR 0004): os geradores em
``dags/melhorias/scripts`` so escrevem o SQL; o operador executa (DBeaver). O script
e idempotente: cria a tabela se faltar e recarrega tudo numa transacao.
"""

from __future__ import annotations

from collections.abc import Sequence

BATCH_SIZE = 1000  # limite de linhas do insert ... values no SQL Server


def sql_text(value: str) -> str:
    """Literal nvarchar com aspas escapadas."""
    escaped = value.replace("'", "''")
    return f"N'{escaped}'"


def render_reload_sql(
    table: str,
    ddl: str,
    columns: Sequence[str],
    values: Sequence[str],
    checks: Sequence[str] = (),
) -> str:
    """DDL + delete + inserts em lotes de ``BATCH_SIZE``, numa transacao.

    ``checks`` rodam depois dos inserts, antes do commit: um ``throw`` neles desfaz a
    carga inteira (``xact_abort on``).
    """
    header = f"insert into {table} ({', '.join(columns)}) values\n"
    inserts = [
        header + ",\n".join(values[i : i + BATCH_SIZE]) + ";"
        for i in range(0, len(values), BATCH_SIZE)
    ]
    return (
        "\n\n".join([
            ddl,
            "set xact_abort on;\nbegin transaction;",
            f"delete from {table};",
            *inserts,
            *checks,
            "commit;",
        ])
        + "\n"
    )
