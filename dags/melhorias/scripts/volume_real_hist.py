"""Gera o script de carga de dbo.mel_volume_real_hist a partir das planilhas do Qlik.

Contexto
--------
``mel_volume_real`` (DAG SILVER_MELHORIAS_VOLUME_REAL) so tem volume a partir de
2025-05, entao o ganho realizado de TC/Aglutinacao/Consumo/Troca MP de 2021-2025
zerava no dbt. O Qlik lia esse volume das planilhas
``BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx`` (aba ``BASE_LANCAMENTO``; os arquivos
"Sobral" trazem os 3 estabelecimentos). Esta tabela traz esse historico para o dbt
(int_ganhos_calc, ADR 0007).

Regras
------
- Colunas usadas: ``Nº F.A.P``, ``Código``, ``1º Mês`` e ``Tipo de Melhoria``, lidas
  de A ate ``cracha`` (alguns arquivos tem uma coluna auxiliar sem nome, ignorada).
- O offset sai do nome do arquivo, nunca da data nem da coluna ``Mês anterior``:
  arquivo normal -> ``1º Mês`` = volume do offset 1 (mes de dt_fap); arquivo
  ``mês.anterior`` -> ``1º Mês`` = volume do offset 2 (mes seguinte). Com isso,
  o offset 2 das FAPs de dezembro (que mora no ``mês.anterior`` do ano seguinte) e
  as linhas com ``Data da FAP`` = dt_fap+60 (erro de data; sao offset 2) ja caem
  no lugar certo.
- Grao da planilha e linha por operacao/mix; o da tabela e
  (numero_fap, cod_prod, mes_offset). Chave em mais de um arquivo (dez/2024 esta em
  2024 e 2025): prevalece o arquivo de ano mais recente. Volumes diferentes da mesma
  chave no mesmo arquivo (linha de mix 0 com volume 0): fica o maior; empate final
  pelo nome do arquivo (resultado deterministico).
- ``cod_prod`` sem zeros a esquerda: o Excel guarda o codigo como numero
  (``0224374`` vira ``224374``) e ``mel_ganhos.cod_prod`` mantem o zero. O dbt
  compara com o codigo de ``mel_ganhos`` tambem sem zeros (int_ganhos_calc).
- ``numero_fap`` com o zero a esquerda de volta: em algumas linhas a celula esta
  como numero e o Excel tirou o zero (``02032024111401`` vira ``2032024111401``); a
  FAP deixava de casar com ``mel_ganhos`` e o volume se perdia. So vale para celula
  numerica que, com o zero, fica no formato da FAP de 14 digitos (``fap_key``).
- Linha sem FAP, codigo ou volume numerico e descartada. Volume 0 e negativo ficam
  (paridade com o Qlik).
- Excecao: linha sem codigo de tipo com ganho por volume (TC, Aglutinacao, Consumo,
  Troca MP) fica, com o codigo ``SEM_CODIGO``. O Qlik calculava o ganho na propria
  linha, sem depender do codigo; ``ganhos_hist.py`` grava o mesmo codigo na linha de
  ganho (ADR 0013).

Carga manual (ADR 0004): o script so gera o SQL; quem executa e o operador, no
SQL Server (DBeaver). O SQL e idempotente: cria a tabela se faltar e recarrega
tudo numa transacao.

Uso
---
    PYTHONPATH=dags uv run python dags/melhorias/scripts/volume_real_hist.py \\
        /caminho/planilhas_volume_real_qlik mel_volume_real_hist.sql
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from melhorias.scripts.sql_reload import render_reload_sql, sql_text

SHEET_NAME = "BASE_LANCAMENTO"
FILE_GLOB = "BASE_LANC_MELHORIAS_*.xlsx"
FILE_PATTERN = re.compile(r"BASE_LANC_MELHORIAS_(\d{4})_\w+\.app\.(.+)\.xlsx")
LAST_COLUMN = "cracha"
TABLE = "dbo.mel_volume_real_hist"
CLI_ARGS = 2  # pasta das planilhas + arquivo .sql de saida

TIPO_HEADER = "Tipo de Melhoria"
# tipos cujo ganho sai de volume real (int_ganhos_calc); os demais usam ganho_previsto
TIPOS_VOLUME = frozenset({"Tempo Ciclo", "Aglutinação", "Consumo", "Troca de Matéria Prima"})
# codigo das linhas sem codigo dos tipos com volume: casa a linha de ganho de
# mel_ganhos_hist com o volume dela (nao comeca com 0: o dbt tira zeros a esquerda)
SEM_CODIGO = "SEM_CODIGO"

# cabecalho da planilha -> coluna da tabela
COLUMN_MAP: dict[str, str] = {
    "Nº F.A.P": "numero_fap",
    "Código": "cod_prod",
    "1º Mês": "volume",
}
KEY = ["numero_fap", "cod_prod", "mes_offset"]
COLUMNS = [*KEY, "volume", "arquivo_origem"]
# FAP de 14 digitos: prefixo de 4 + data AAAAMMDD + sequencial de 2
FAP_PATTERN = re.compile(r"\d{4}20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{2}")

# collation igual a mel_ganhos/mel_volume_real: join sem COLLATE no dbt
DDL = f"""if object_id('{TABLE}', 'U') is null
create table {TABLE} (
    numero_fap varchar(30) collate Latin1_General_100_CI_AS_SC_UTF8 not null,
    cod_prod varchar(255) collate Latin1_General_100_CI_AS_SC_UTF8 not null,
    mes_offset tinyint not null,
    volume decimal(18,4) not null,
    arquivo_origem varchar(100) collate Latin1_General_100_CI_AS_SC_UTF8 not null,
    constraint mel_volume_real_hist_pk primary key (numero_fap, cod_prod, mes_offset),
    constraint mel_volume_real_hist_offset_ck check (mes_offset in (1, 2))
);"""


class VolumeHistError(ValueError):
    """Planilha de volume real historico fora do formato esperado."""


def parse_filename(name: str) -> tuple[int, int]:
    """Nome do arquivo -> (ano do arquivo, mes_offset do ``1º Mês``)."""
    match = FILE_PATTERN.fullmatch(unicodedata.normalize("NFC", name))
    if not match:
        raise VolumeHistError(f"arquivo fora do padrao BASE_LANC_MELHORIAS_<ano>_*: {name}")
    ano, sufixo = match.groups()
    return int(ano), 2 if "anterior" in sufixo else 1


def read_spreadsheet(path: Path) -> pd.DataFrame:
    """Aba BASE_LANCAMENTO crua (colunas ate ``cracha``) + coluna ``arquivo``."""
    df = pd.read_excel(path, sheet_name=SHEET_NAME, engine="calamine", dtype=object)
    df = df.rename(columns=lambda c: str(c).strip())
    df = df[[c for c in df.columns if not c.startswith("Unnamed")]]
    if LAST_COLUMN in df.columns:
        df = df.iloc[:, : list(df.columns).index(LAST_COLUMN) + 1]
    return df.assign(arquivo=unicodedata.normalize("NFC", path.name))


def cell_str(value: object) -> str | None:
    """Celula de texto do Excel: numero inteiro sem ``.0``, vazio vira None."""
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip() or None


def fap_key(value: object) -> str | None:
    """Numero da FAP, com o zero a esquerda que o Excel tirou da celula numerica.

    Celula de texto fica como esta: existe FAP de 13 digitos no SharePoint. Numero que
    nem com o zero fica no formato de 14 digitos (FAP antiga de Crato) tambem.
    """
    text = cell_str(value)
    if text and isinstance(value, (int, float)) and FAP_PATTERN.fullmatch(f"0{text}"):
        return f"0{text}"
    return text


def cod_prod_key(value: object) -> str | None:
    """Codigo do produto sem zeros a esquerda (chave canonica, ADR 0007)."""
    text = cell_str(value)
    return (text.lstrip("0") or None) if text else None


def volume_cod_prod(cod_prod: pd.Series, tipo: pd.Series) -> pd.Series:
    """Codigo canonico; linha sem codigo de tipo com volume vira ``SEM_CODIGO``."""
    cod = cod_prod.map(cod_prod_key).astype(object)
    sem_codigo = cod.isna() & tipo.map(cell_str).isin(TIPOS_VOLUME)
    return cod.mask(sem_codigo, SEM_CODIGO)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas cruas das planilhas -> uma linha por (numero_fap, cod_prod, mes_offset)."""
    missing = [c for c in [*COLUMN_MAP, TIPO_HEADER, "arquivo"] if c not in df.columns]
    if missing:
        raise VolumeHistError(f"colunas ausentes na planilha: {missing}")

    arquivos = {a: parse_filename(a) for a in df.arquivo.unique()}
    out = df[[*COLUMN_MAP, "arquivo"]].rename(columns=COLUMN_MAP)
    out = out.assign(
        numero_fap=out.numero_fap.map(fap_key),
        cod_prod=volume_cod_prod(out.cod_prod, df[TIPO_HEADER]),
        volume=pd.to_numeric(out.volume, errors="coerce").astype(float),
        ano_arquivo=out.arquivo.map(lambda a: arquivos[a][0]),
        mes_offset=out.arquivo.map(lambda a: arquivos[a][1]),
        arquivo_origem=out.arquivo,
    ).dropna(subset=["numero_fap", "cod_prod", "volume"])

    return (
        out
        .sort_values(["ano_arquivo", "volume", "arquivo_origem"], ascending=False)
        .drop_duplicates(KEY)
        .sort_values(KEY)
        .reset_index(drop=True)[COLUMNS]
    )


def _values(row) -> str:
    return (
        f"({sql_text(row.numero_fap)}, {sql_text(row.cod_prod)}, {int(row.mes_offset)}, "
        f"{float(row.volume)!r}, {sql_text(row.arquivo_origem)})"
    )


def render_sql(df: pd.DataFrame) -> str:
    """Script idempotente: DDL + recarga completa numa transacao."""
    values = [_values(r) for r in df.itertuples(index=False)]
    return render_reload_sql(TABLE, DDL, COLUMNS, values)


def main(argv: list[str]) -> int:
    if len(argv) != CLI_ARGS:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = map(Path, argv)
    files = sorted(src.glob(FILE_GLOB))
    if not files:
        raise VolumeHistError(f"nenhuma planilha {FILE_GLOB} em {src}")
    raw = pd.concat([read_spreadsheet(f) for f in files], ignore_index=True)
    df = normalize(raw)
    out.write_text(render_sql(df), encoding="utf-8")
    print(f"{len(raw)} linhas de {len(files)} planilhas -> {len(df)} chaves -> {out}")
    print(df.groupby(["mes_offset", "arquivo_origem"]).size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
