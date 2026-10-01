"""Gera o script de carga de dbo.mel_carga_horaria_macro a partir da planilha do Qlik.

Contexto
--------
O Qlik convertia horas ganhas em pessoas/R$ com a planilha ``carga_horaria.xlsx``
(aba ``carga horaria``), chave ``estabelecimento | Area | mes``: carga por macro
setor. ``mel_carga_horaria`` (por setor) so existe a partir de 2024-09 e tem
setores com 0, entao o ganho em pessoas de 2021-2025 zerava no dbt. Esta tabela
traz o historico da planilha para o dbt (int_ganhos_calc).

Regras
------
- Colunas usadas: ``estabelecimento``, ``Area``, ``data``, ``h/mês/Func``.
- Texto sem espacos nas pontas; ``data`` truncada no primeiro dia do mes.
- Duplicata exata da chave e descartada; chave repetida com carga diferente e
  erro (corrigir a planilha), assim como carga nula ou <= 0.

Carga manual (ADR 0004): o script so gera o SQL; quem executa e o operador, no
SQL Server (DBeaver). O SQL e idempotente: cria a tabela se faltar e recarrega
tudo numa transacao.

Uso
---
    PYTHONPATH=dags uv run python dags/melhorias/scripts/carga_horaria_macro.py \\
        /caminho/carga_horaria.xlsx mel_carga_horaria_macro.sql
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from melhorias.scripts.sql_reload import render_reload_sql, sql_text

SHEET_NAME = "carga horaria"
TABLE = "dbo.mel_carga_horaria_macro"
CLI_ARGS = 2  # planilha de entrada + arquivo .sql de saida

# cabecalho da planilha -> coluna da tabela
COLUMN_MAP: dict[str, str] = {
    "estabelecimento": "estabelecimento",
    "Area": "area",
    "data": "mes",
    "h/mês/Func": "ch_mensal",
}
KEY = ["estabelecimento", "area", "mes"]

DDL = f"""if object_id('{TABLE}', 'U') is null
create table {TABLE} (
    estabelecimento varchar(100) collate Latin1_General_100_CI_AS_SC_UTF8 not null,
    area varchar(255) collate Latin1_General_100_CI_AS_SC_UTF8 not null,
    mes date not null,
    ch_mensal decimal(18,6) not null,
    constraint mel_carga_horaria_macro_pk primary key (estabelecimento, area, mes)
);"""


class CargaHorariaError(ValueError):
    """Planilha de carga horaria fora do formato esperado."""


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Planilha crua -> linhas unicas por (estabelecimento, area, mes)."""
    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise CargaHorariaError(f"colunas ausentes na planilha: {missing}")

    out = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    out = out.assign(
        estabelecimento=out.estabelecimento.astype(str).str.strip(),
        area=out.area.astype(str).str.strip(),
        mes=pd.to_datetime(out.mes).dt.to_period("M").dt.to_timestamp(),
        ch_mensal=pd.to_numeric(out.ch_mensal, errors="coerce"),
    )

    invalid = out[out.ch_mensal.isna() | (out.ch_mensal <= 0)]
    if not invalid.empty:
        raise CargaHorariaError(
            f"h/mês/Func nulo ou <= 0 em {len(invalid)} linha(s): {_keys(invalid)}"
        )

    out = out.drop_duplicates()
    conflicts = out[out.duplicated(KEY, keep=False)]
    if not conflicts.empty:
        raise CargaHorariaError(
            f"chave repetida com h/mês/Func diferente: {_keys(conflicts.drop_duplicates(KEY))}"
        )

    return out.sort_values(KEY).reset_index(drop=True)


def _keys(df: pd.DataFrame) -> str:
    return ", ".join(
        f"{r.estabelecimento}|{r.area}|{r.mes:%Y-%m}" for r in df.head(20).itertuples()
    )


def _values(row) -> str:
    return (
        f"({sql_text(row.estabelecimento)}, {sql_text(row.area)}, "
        f"'{row.mes:%Y-%m-%d}', {float(row.ch_mensal)!r})"
    )


def render_sql(df: pd.DataFrame) -> str:
    """Script idempotente: DDL + recarga completa numa transacao."""
    values = [_values(r) for r in df.itertuples(index=False)]
    return render_reload_sql(TABLE, DDL, list(COLUMN_MAP.values()), values)


def main(argv: list[str]) -> int:
    if len(argv) != CLI_ARGS:
        print(__doc__, file=sys.stderr)
        return 2
    xlsx, out = map(Path, argv)
    df = normalize(pd.read_excel(xlsx, sheet_name=SHEET_NAME))
    out.write_text(render_sql(df), encoding="utf-8")
    print(f"{len(df)} linhas -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
