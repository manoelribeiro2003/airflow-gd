"""Gera o SQL que insere em dbo.mel_aprovacao FAPs aprovadas que ficaram fora da carga.

Contexto
--------
A carga historica de ``mel_aprovacao`` (export do SharePoint, 2021-2025) separou as
FAPs com status Aprovado sem nenhuma data (sem ``dt_fap``, sem ``dt_aprovacao_eng`` e
sem linha de ganho) e as criadas antes de 2021. Nenhuma delas foi carregada. Parte
dessas FAPs esta lancada nas planilhas ``BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx``
que alimentavam o Qlik, com ``Data da FAP`` e ganho: sem a linha em ``mel_aprovacao``
o dbt nao conta a FAP (ADR 0003) e ``mel_ganhos_hist`` nao pode recebe-la (ADR 0008).
Issue #27.

Regras
------
- Entrada: parquets com as linhas de ``mel_aprovacao`` ja no schema do banco (mesmos
  nomes e tipos de coluna), gerados na carga historica. So entra status Aprovado.
- So entra FAP lancada nas planilhas: mesma selecao de ``ganhos_hist.normalize``
  (arquivos normais, linha com tipo, arquivo mais recente da FAP).
- ``dt_fap`` = ``Data da FAP`` da planilha (a menor da FAP), a mesma data que
  ``mel_ganhos_hist`` grava. Sem data na planilha, fica a da linha; sem nenhuma das
  duas a FAP nao entra (FAP anterior a 2025 sem data e descartada).
- ``tipo_melhoria`` vazio na linha e completado com o tipo da planilha.

Carga manual (ADR 0004): o script so gera o SQL; o operador executa no SQL Server
(DBeaver). Tudo numa transacao; se algum ``ID`` ou ``numero_fap`` ja existir em
``mel_aprovacao`` o script para sem gravar nada. Rodar antes de gerar a lista de FAPs
de ``ganhos_hist.py``.

Uso
---
    PYTHONPATH=dags uv run python dags/melhorias/scripts/aprovacao_planilha.py \\
        /caminho/planilhas_volume_real_qlik saida.sql aprovado_sem_dt_fap.parquet [...]
"""

from __future__ import annotations

import datetime as dt
import math
import sys
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from melhorias.scripts.ganhos_hist import normalize
from melhorias.scripts.sql_reload import BATCH_SIZE, sql_text
from melhorias.scripts.volume_real_hist import FILE_GLOB, read_spreadsheet

TABLE = "dbo.mel_aprovacao"
MIN_ARGS = 3  # pasta das planilhas + arquivo .sql de saida + ao menos um parquet


class AprovacaoPlanilhaError(ValueError):
    """Entrada fora do formato esperado."""


def planilha_faps(raw: pd.DataFrame, faps: Iterable[str]) -> pd.DataFrame:
    """``numero_fap`` -> ``dt_fap`` e ``tipo_melhoria`` da planilha (uma linha por FAP)."""
    rows = normalize(raw, faps)
    return (
        rows
        .groupby("numero_fap")
        .agg(dt_planilha=("dt_fap", "first"), tipo_planilha=("tipo_melhoria", "first"))
        .reset_index()
    )


def select_rows(aprovacao: pd.DataFrame, planilha: pd.DataFrame) -> pd.DataFrame:
    """Linhas aprovadas lancadas na planilha, com ``dt_fap`` e tipo da planilha."""
    if aprovacao.numero_fap.duplicated().any() or aprovacao.ID.duplicated().any():
        raise AprovacaoPlanilhaError("ID ou numero_fap repetido nas linhas de entrada")
    rows = aprovacao[aprovacao.status == "Aprovado"].merge(planilha, on="numero_fap")
    dt_planilha = pd.to_datetime(rows.dt_planilha)
    rows = rows.assign(
        dt_fap=dt_planilha.fillna(pd.to_datetime(rows.dt_fap)),
        tipo_melhoria=rows.tipo_melhoria.fillna(rows.tipo_planilha),
    )
    return rows[rows.dt_fap.notna()][list(aprovacao.columns)].reset_index(drop=True)


def _literal(value: object) -> str:
    if value is None or value is pd.NaT or (isinstance(value, float) and math.isnan(value)):
        return "null"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, dt.datetime):  # pd.Timestamp tambem
        return f"'{value.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}'"
    if isinstance(value, dt.date):
        return f"'{value.isoformat()}'"
    if isinstance(value, (int, float)):  # int com nulo chega como float: 13783497.0
        return str(int(value)) if float(value).is_integer() else repr(value)
    return sql_text(str(value))


def render_sql(rows: pd.DataFrame) -> str:
    """Inserts em lotes numa transacao, com trava contra linha que ja existe."""
    columns = ", ".join(f"[{c}]" for c in rows.columns)
    records = rows.astype(object).where(rows.notna(), None).to_dict("records")
    values = ["(" + ", ".join(_literal(v) for v in r.values()) + ")" for r in records]
    ids = ", ".join(str(int(i)) for i in rows.ID)
    faps = ", ".join(sql_text(f) for f in rows.numero_fap)
    guard = f"""if exists (
    select 1 from {TABLE}
    where ID in ({ids}) or numero_fap in ({faps})
)
    throw 50003, N'mel_aprovacao: ID ou numero_fap ja carregado; nada foi gravado', 1;"""
    inserts = [
        f"insert into {TABLE} ({columns}) values\n" + ",\n".join(values[i : i + BATCH_SIZE]) + ";"
        for i in range(0, len(values), BATCH_SIZE)
    ]
    return (
        "\n\n".join(["set xact_abort on;\nbegin transaction;", guard, *inserts, "commit;"]) + "\n"
    )


def main(argv: list[str]) -> int:
    if len(argv) < MIN_ARGS:
        print(__doc__, file=sys.stderr)
        return 2
    src, out, *parquets = map(Path, argv)
    files = sorted(src.glob(FILE_GLOB))
    if not files:
        raise AprovacaoPlanilhaError(f"nenhuma planilha {FILE_GLOB} em {src}")
    aprovacao = pd.concat([pd.read_parquet(p) for p in parquets], ignore_index=True)
    raw = pd.concat([read_spreadsheet(f) for f in files], ignore_index=True)
    rows = select_rows(aprovacao, planilha_faps(raw, set(aprovacao.numero_fap)))
    out.write_text(render_sql(rows), encoding="utf-8")
    print(f"{len(aprovacao)} linhas de entrada, {len(rows)} lancadas na planilha -> {out}")
    anos = rows.dt_fap.dt.year
    print(rows.assign(ano=anos).groupby(["ano", "tipo_melhoria"]).numero_fap.size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
