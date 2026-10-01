"""Gera o script de carga de dbo.mel_ganhos_hist a partir das planilhas do Qlik.

Contexto
--------
Parte das FAPs aprovadas em ``mel_aprovacao`` nao tem nenhuma linha em ``mel_ganhos``
(quase todas de 2021 e 2023). O dado de ganho delas (componentes, TC, consumo, custo
par, ganho em R$, idealizador) so existe nas planilhas
``BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx`` (aba ``BASE_LANCAMENTO``) que
alimentavam o Qlik. Esta tabela traz essas linhas para o dbt: ``stg_mel_ganhos`` faz
``union all`` com o bronze (ADR 0008). O volume realizado dos tipos com ganho por
volume vem de ``mel_volume_real_hist`` (ADR 0007); o ganho dos demais tipos e o
``Ganho mês R$`` da planilha, gravado em ``ganho_previsto``.

Tambem entram as FAPs do seed ``mel_ganhos_fonte_planilha``: tem linha em
``mel_ganhos``, mas o cadastro de la esta incompleto ou diferente da planilha, e a area
confirmou a planilha. ``stg_mel_ganhos`` tira essas FAPs do bronze e usa as linhas
daqui (ADR 0013).

Regras
------
- Selecao: FAP presente na lista ``numero_fap`` (export da query abaixo: aprovadas
  sem nenhuma linha em ``mel_ganhos``) ou no seed ``mel_ganhos_fonte_planilha`` (lido
  do CSV do repo), e linha com tipo de melhoria. Fora as FAPs do seed, uma FAP nunca
  existe nas duas fontes; o SQL gerado confere de novo na hora da carga e desfaz tudo
  se a lista estiver velha.
- So arquivos normais: o ``mês.anterior`` repete as linhas da FAP com a data
  deslocada e so serve de volume do offset 2.
- FAP em mais de um arquivo normal (dez/2024 esta em 2024 e 2025): a FAP inteira vem
  do arquivo mais recente.
- Tipos com ganho por volume (TC, Aglutinacao, Consumo, Troca MP): grao da planilha
  (linha por operacao/mix), todas as linhas ficam, como no Qlik. Linha sem codigo fica
  com o codigo ``SEM_CODIGO``, o mesmo que ``mel_volume_real_hist`` da ao volume dela.
  ``ganho_previsto`` nulo (a planilha nao tem volume previsto).
- Demais tipos ("Outros"): uma linha por FAP, com ``ganho_previsto`` = ``Ganho mês R$``.
  O ganho e da FAP, nao do componente: a planilha repete a linha em algumas FAPs e o
  Qlik somava em dobro; linha repetida com o mesmo ganho conta uma vez. Linhas da
  mesma FAP com ganhos diferentes somam (issue #27).
  ``Ganho mês R$`` vem como texto pt-BR nas planilhas 2021-2024 (``"40286,88"``).
- ``id`` sequencial pela FAP/codigo (deterministico), unico so dentro desta tabela.
- ``cod_prod`` sem zeros a esquerda, igual a ``mel_volume_real_hist``.
- ``numero_fap`` com o zero a esquerda que o Excel tira da celula numerica, tambem
  igual a ``mel_volume_real_hist`` (``fap_key``).
- Campos sem equivalente na planilha (id_solicitacao_assinatura, tipo_fap, fabrica,
  gerente, cc_idealizador) sao completados no dbt a partir de ``mel_aprovacao``.

Query da lista de FAPs (DBeaver, exportar CSV com cabecalho ``numero_fap``)::

    select a.numero_fap
    from dbo.mel_aprovacao as a
    where a.status = 'Aprovado'
        and not exists (
            select 1 from dbo.mel_ganhos as g where g.numero_fap = a.numero_fap
        )

Carga manual (ADR 0004): o script so gera o SQL; quem executa e o operador, no
SQL Server (DBeaver, execucao de script: um comando por vez). O SQL e idempotente:
cria a tabela se faltar, migra a tabela anterior a issue #25 e recarrega tudo numa
transacao. A conferencia da carga le ``dbo.mel_ganhos_fonte_planilha``: carregar o
seed antes.

Uso
---
    PYTHONPATH=dags uv run python dags/melhorias/scripts/ganhos_hist.py \\
        /caminho/planilhas_volume_real_qlik faps_sem_ganhos.csv mel_ganhos_hist.sql
"""

from __future__ import annotations

import math
import sys
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from melhorias.scripts.sql_reload import render_reload_sql, sql_text
from melhorias.scripts.volume_real_hist import (
    FILE_GLOB,
    SEM_CODIGO,
    TIPOS_VOLUME,
    cell_str,
    cod_prod_key,
    fap_key,
    parse_filename,
    read_spreadsheet,
)

TABLE = "dbo.mel_ganhos_hist"
CLI_ARGS = 3  # pasta das planilhas + CSV da lista de FAPs + arquivo .sql de saida
INT_MAX = 2**31 - 1
# FAPs com linha em mel_ganhos cujo ganho vem da planilha (ADR 0013)
FONTE_PLANILHA_SEED = (
    Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "mel_ganhos_fonte_planilha.csv"
)

GANHO_HEADER = "Ganho mês R$"

TEXT = "text"
NUMBER = "number"
INT = "int"
DATE = "date"

# cabecalho da planilha -> (coluna da tabela, tipo)
COLUMN_MAP: dict[str, tuple[str, str]] = {
    "Nº F.A.P": ("numero_fap", TEXT),
    "Código": ("cod_prod", TEXT),
    "Data da FAP": ("dt_fap", DATE),
    "Tipo de Melhoria": ("tipo_melhoria", TEXT),
    "Estab.": ("filial", TEXT),
    "Setor": ("setor", TEXT),
    "Setor Macro": ("macro_setor", TEXT),
    "T.C. Anterior": ("tc_anterior", NUMBER),
    "T.C. Atual": ("tc_atual", NUMBER),
    "MIX": ("mix", NUMBER),
    "Cons_Anterior": ("consumo_anterior", NUMBER),
    "Cons_Atual": ("consumo_atual", NUMBER),
    "Preço M.P.": ("preco_mp", NUMBER),
    "Custo Par Anterior": ("custo_par_anterior", NUMBER),
    "Custo Par Atual": ("custo_par_atual", NUMBER),
    GANHO_HEADER: ("ganho_previsto", NUMBER),
    "cracha": ("cracha_idealizador", INT),
    "Idealizador": ("nome_idealizador", TEXT),
    "Gerente idealizador": ("gerente_idealizador", TEXT),
    "Cargo": ("cargo", TEXT),
    "Origem": ("origem_melhoria", TEXT),
    "É replicação": ("replicacao", TEXT),
}
KINDS = {"id": INT, **dict(COLUMN_MAP.values()), "arquivo_origem": TEXT}
COLUMNS = list(KINDS)
NUMBER_COLUMNS = [c for c, k in KINDS.items() if k == NUMBER]
# atributos da FAP (nao do componente): fct_ganhos agrupa por eles
FAP_COLUMNS = (
    "filial",
    "setor",
    "macro_setor",
    "cracha_idealizador",
    "nome_idealizador",
    "gerente_idealizador",
    "cargo",
    "origem_melhoria",
    "replicacao",
)

# tipos e collation iguais a mel_ganhos: union all no dbt sem mudar tipo nem COLLATE
_UTF8 = "collate Latin1_General_100_CI_AS_SC_UTF8"
DDL = f"""if object_id('{TABLE}', 'U') is null
create table {TABLE} (
    id int not null,
    numero_fap varchar(30) {_UTF8} not null,
    cod_prod varchar(255) {_UTF8} null,
    dt_fap date null,
    tipo_melhoria varchar(255) {_UTF8} not null,
    filial varchar(255) {_UTF8} null,
    setor varchar(255) {_UTF8} null,
    macro_setor varchar(255) {_UTF8} null,
    tc_anterior real null,
    tc_atual real null,
    mix real null,
    consumo_anterior real null,
    consumo_atual real null,
    preco_mp decimal(18,2) null,
    custo_par_anterior real null,
    custo_par_atual real null,
    ganho_previsto decimal(18,2) null,
    cracha_idealizador int null,
    nome_idealizador varchar(255) {_UTF8} null,
    gerente_idealizador varchar(255) {_UTF8} null,
    cargo varchar(255) {_UTF8} null,
    origem_melhoria varchar(255) {_UTF8} null,
    replicacao varchar(255) {_UTF8} null,
    arquivo_origem varchar(100) {_UTF8} not null,
    constraint mel_ganhos_hist_pk primary key (id)
);

-- tabela criada antes da issue #25 (so tipos com volume): coluna nova e codigo opcional
if col_length('{TABLE}', 'ganho_previsto') is null
    alter table {TABLE} add ganho_previsto decimal(18,2) null;

alter table {TABLE} alter column cod_prod varchar(255) {_UTF8} null;"""

# conferidos na hora da carga (a lista de FAPs pode ter ficado velha): throw desfaz tudo.
# FAP de mel_ganhos_fonte_planilha pode ter linha em mel_ganhos: o dbt tira do bronze.
CHECKS = (
    f"""if exists (
    select 1 from {TABLE} as h
    where exists (select 1 from dbo.mel_ganhos as g where g.numero_fap = h.numero_fap)
        and not exists (
            select 1 from dbo.mel_ganhos_fonte_planilha as p
            where p.numero_fap = h.numero_fap
        )
)
    throw 50001, N'mel_ganhos_hist: FAP ja tem linha em mel_ganhos; gere a lista de novo', 1;""",
    f"""if exists (
    select 1 from {TABLE} as h
    where not exists (
        select 1 from dbo.mel_aprovacao as a
        where a.numero_fap = h.numero_fap and a.status = 'Aprovado'
    )
)
    throw 50002, N'mel_ganhos_hist: FAP nao esta aprovada; gere a lista de novo', 1;""",
)


class GanhosHistError(ValueError):
    """Planilha ou lista de FAPs fora do formato esperado."""


def read_faps(path: Path) -> set[str]:
    """CSV exportado da query do docstring -> conjunto de ``numero_fap``."""
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", skip_blank_lines=True)
    df = df.rename(columns=lambda c: str(c).strip().lower())
    if "numero_fap" not in df.columns:
        raise GanhosHistError(f"coluna numero_fap ausente em {path}")
    return {f for f in df.numero_fap.map(cell_str) if f}


def _int(number: float) -> int | None:
    if math.isnan(number) or not number.is_integer() or abs(number) > INT_MAX:
        return None
    return int(number)


def parse_ganho(value: object) -> float | None:
    """``Ganho mês R$``: numero nativo ou texto pt-BR (``"40286,88"``, ``"-0,27"``).

    ``pd.to_numeric(errors="coerce")`` transforma o texto com virgula em NaN e zerava o
    ganho; texto que nao e numero para o script em vez de virar nulo.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).strip()
    if not text:
        return None
    try:
        return round(float(text.replace(",", ".")), 2)
    except ValueError:
        raise GanhosHistError(f"{GANHO_HEADER} invalido: {value!r}") from None


def _convert(series: pd.Series, column: str, kind: str) -> pd.Series:
    if column == "ganho_previsto":
        return series.map(parse_ganho).astype(float)
    if column == "cod_prod":
        return series.map(cod_prod_key).astype(object)
    if column == "numero_fap":
        return series.map(fap_key).astype(object)
    if kind == TEXT:
        return series.map(cell_str).astype(object)
    if kind == DATE:
        stamps = pd.to_datetime(series, errors="coerce")
        return stamps.map(lambda s: None if pd.isna(s) else s.date()).astype(object)
    numbers = pd.to_numeric(series, errors="coerce").astype(float)
    return numbers.map(_int).astype(object) if kind == INT else numbers


def _latest_file_rows(df: pd.DataFrame) -> pd.DataFrame:
    """FAP em mais de um arquivo normal: so as linhas do arquivo mais recente."""
    ranked = df.assign(_ano=df.arquivo_origem.map(lambda a: parse_filename(a)[0]))
    latest = ranked.sort_values(["_ano", "arquivo_origem"]).drop_duplicates(
        "numero_fap", keep="last"
    )[["numero_fap", "arquivo_origem"]]
    return ranked.merge(latest, on=["numero_fap", "arquivo_origem"]).drop(columns="_ano")


def _one_row_per_fap(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos sem volume: uma linha por FAP com a soma dos ganhos distintos.

    Linha repetida com o mesmo ganho nao soma de novo; ganhos diferentes na mesma FAP
    (FAO de 2021 com um lancamento por posto) somam, como no Qlik.
    """
    distintos = df.drop_duplicates(["numero_fap", "ganho_previsto"])
    total = distintos.groupby("numero_fap").ganho_previsto.sum(min_count=1)
    first = df.drop_duplicates("numero_fap")
    return first.assign(ganho_previsto=first.numero_fap.map(total).round(2))


def _none_if_na(series: pd.Series) -> pd.Series:
    return series.astype(object).map(lambda v: None if pd.isna(v) else v)


def _same_per_fap(df: pd.DataFrame) -> pd.DataFrame:
    """Atributos da FAP iguais em todas as linhas: data menor, demais o 1o nao nulo."""
    por_fap = df.groupby("numero_fap")
    dt_fap = por_fap.dt_fap.transform(lambda s: min(s.dropna(), default=None))
    return df.assign(
        dt_fap=_none_if_na(dt_fap),
        **{c: _none_if_na(por_fap[c].transform("first")) for c in FAP_COLUMNS},
    )


def normalize(df: pd.DataFrame, faps: Iterable[str]) -> pd.DataFrame:
    """Linhas cruas das planilhas -> linhas de mel_ganhos_hist das FAPs da lista."""
    missing = [c for c in [*COLUMN_MAP, "arquivo"] if c not in df.columns]
    if missing:
        raise GanhosHistError(f"colunas ausentes na planilha: {missing}")

    arquivos = {a: parse_filename(a) for a in df.arquivo.unique()}
    selected = df[
        df.arquivo.map(lambda a: arquivos[a][1] == 1)
        & df["Nº F.A.P"].map(fap_key).isin(set(faps))
        & df["Tipo de Melhoria"].map(cell_str).notna()
    ]
    out = pd.DataFrame({
        col: _convert(selected[header], col, kind) for header, (col, kind) in COLUMN_MAP.items()
    }).assign(arquivo_origem=selected.arquivo)
    out = _latest_file_rows(out).sort_values(
        ["numero_fap", "cod_prod", *NUMBER_COLUMNS], kind="stable"
    )

    volume = out.tipo_melhoria.isin(TIPOS_VOLUME)
    out = pd.concat([
        out[volume].assign(
            cod_prod=out.cod_prod[volume].fillna(SEM_CODIGO), ganho_previsto=float("nan")
        ),
        _one_row_per_fap(out[~volume]),
    ]).sort_values(["numero_fap", "cod_prod", *NUMBER_COLUMNS], kind="stable")
    out = _same_per_fap(out)
    return out.assign(id=range(1, len(out) + 1)).reset_index(drop=True)[COLUMNS]


def _literal(value: object, kind: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "null"
    if kind == TEXT:
        return sql_text(str(value))
    if kind == DATE:
        return f"'{value.isoformat()}'"  # type: ignore[attr-defined]
    if kind == INT:
        return str(int(value))  # type: ignore[call-overload]
    return repr(float(value))  # type: ignore[arg-type]


def _values(row: dict[str, object]) -> str:
    return "(" + ", ".join(_literal(row[c], KINDS[c]) for c in COLUMNS) + ")"


def render_sql(df: pd.DataFrame) -> str:
    """Script idempotente: DDL + recarga completa + conferencia, numa transacao."""
    values = [_values(r) for r in df[COLUMNS].to_dict("records")]
    return render_reload_sql(TABLE, DDL, COLUMNS, values, CHECKS)


def main(argv: list[str]) -> int:
    if len(argv) != CLI_ARGS:
        print(__doc__, file=sys.stderr)
        return 2
    src, faps_csv, out = map(Path, argv)
    files = sorted(src.glob(FILE_GLOB))
    if not files:
        raise GanhosHistError(f"nenhuma planilha {FILE_GLOB} em {src}")
    faps = read_faps(faps_csv) | read_faps(FONTE_PLANILHA_SEED)
    raw = pd.concat([read_spreadsheet(f) for f in files], ignore_index=True)
    df = normalize(raw, faps)
    out.write_text(render_sql(df), encoding="utf-8")
    print(
        f"{len(faps)} FAPs na lista, {df.numero_fap.nunique()} nas planilhas "
        f"-> {len(df)} linhas -> {out}"
    )
    anos = pd.to_datetime(df.dt_fap).dt.year.astype("Int64")
    print(df.assign(ano=anos).groupby(["ano", "tipo_melhoria"]).numero_fap.nunique().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
