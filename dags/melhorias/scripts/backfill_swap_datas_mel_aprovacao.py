"""Backfill one-off: corrige datas legadas com dia/mes trocados em mel_aprovacao.

Contexto
--------
Linhas ingeridas antes do fix de parse do SharePoint (datetime_resolve.py,
2026-06-04) usavam ``pd.to_datetime(dayfirst=False)`` (month-first). Datas
ambiguas ``dd/MM`` cruas (ex.: "12/02/2026" = 12-fev) foram gravadas com dia e
mes invertidos ("2026-12-02"), gerando bimestres futuros em mel_fct_melhoria.

O parser atual ja resolve corretamente; estas linhas nunca foram reprocessadas
porque o ``Modified`` caiu fora da janela de fetch de 90 dias e o merge e keyed
em ``Modified`` (origem == destino).

Estrategia
----------
Para cada coluna afetada, sobre linhas com ``[col] > getdate()`` (futuro =
sintoma do swap):

1. ``swapped = datetimefromparts(year, day, month, hh, mm, ss)`` apenas quando
   ``day([col]) between 1 and 12`` (senao o swap seria mes invalido).
2. Aplica UPDATE somente quando ``swapped <= getdate()`` E ``swapped`` cai na
   janela da ancora ``[Created-2d, Modified+2d]``. Linhas que nao validam sao
   logadas e deixadas intactas para revisao manual.

Idempotente: a condicao ``[col] > getdate()`` torna re-execucao um no-op.
Transacional: tudo num unico commit; rollback em qualquer erro.

Uso
---
    docker exec airflow-airflow-worker-1 \
        python /opt/airflow/dags/melhorias/scripts/backfill_swap_datas_mel_aprovacao.py
"""

import sys

sys.path.insert(0, "/opt/airflow/dags")

from global_modules.database import get_eng_conn
from sqlalchemy import text

TABLE = "dbo.mel_aprovacao"

# Colunas com o swap dia/mes legado. dt_aprovacao_analista e UTC, mas o swap e
# puramente dia<->mes; a janela da ancora (+/-2d) absorve o offset de fuso.
AFFECTED_COLUMNS = (
    "dt_aprovacao_eng",
    "dt_aprovacao_producao",
    "dt_inicio_fluxo",
    "dt_fap",
    "dt_aprovacao_analista",
)


def _swapped_expr(col):
    """Expressao SQL que troca dia<->mes preservando ano e hora."""
    return (
        f"datetimefromparts(year([{col}]), day([{col}]), month([{col}]), "
        f"datepart(hour,[{col}]), datepart(minute,[{col}]), datepart(second,[{col}]), 0)"
    )


def _count_query(col):
    swapped = _swapped_expr(col)
    return text(
        f"""
        with fut as (
          select [{col}] as v, Created, Modified,
                 case when day([{col}]) between 1 and 12 then {swapped} end as swapped
          from {TABLE}
          where [{col}] > getdate()
        )
        select
          count(*) as futuros,
          sum(case when swapped is not null
                    and swapped <= getdate()
                    and swapped between dateadd(day,-2,Created) and dateadd(day,2,Modified)
                   then 1 else 0 end) as validados
        from fut
        """
    )


def _update_query(col):
    swapped = _swapped_expr(col)
    return text(
        f"""
        update {TABLE}
        set [{col}] = {swapped}
        where [{col}] > getdate()
          and day([{col}]) between 1 and 12
          and {swapped} <= getdate()
          and {swapped} between dateadd(day,-2,Created) and dateadd(day,2,Modified)
        """
    )


def main():
    eng = get_eng_conn()
    with eng.begin() as c:  # transacional: commit no sucesso, rollback no erro
        for col in AFFECTED_COLUMNS:
            row = c.execute(_count_query(col)).fetchone()
            futuros, validados = row[0], (row[1] or 0)
            nao_validam = futuros - validados

            if futuros == 0:
                print(f"{col:24s} sem linhas futuras (no-op)")
                continue

            result = c.execute(_update_query(col))
            print(
                f"{col:24s} futuros={futuros:4d} validados={validados:4d} "
                f"atualizados={result.rowcount:4d} pendentes_revisao={nao_validam:4d}"
            )
            if nao_validam:
                print(
                    f"  ATENCAO: {nao_validam} linha(s) de {col} nao validaram a "
                    f"janela da ancora e ficaram intactas para revisao manual."
                )

    print("Backfill concluido (commit).")


if __name__ == "__main__":
    main()
