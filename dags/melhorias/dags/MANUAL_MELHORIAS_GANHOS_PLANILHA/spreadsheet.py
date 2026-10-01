"""Leitura e normalizacao da planilha de ganhos importada manualmente.

A planilha substitui a lista do SharePoint quando a FAP tem linhas demais para a
lista suportar. Aqui so tratamos formato: nomes de coluna, tipos e linhas vazias.
Regras de negocio (FAP aprovada, linha base em mel_ganhos) ficam no SQL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# cabecalho da planilha (sem espacos nas pontas) -> coluna de mel_ganhos
COLUMN_MAP: dict[str, str] = {
    "Tipo de Melhoria": "tipo_melhoria",
    "Estab.": "filial",
    "Setor": "setor",
    "Processista": "nome_solicitante",
    "Nº F.A.P": "numero_fap",
    "Data da FAP": "dt_fap",
    "Código": "cod_prod",
    "Preço M.P.": "preco_mp",
    "Cons_Anterior": "consumo_anterior",
    "Cons_Atual": "consumo_atual",
    "Padrão Anterior": "padrao_anterior",
    "Padrão Atual": "padrao_atual",
    "Efetivo Anterior": "efetivo_anterior",
    "Efetivo Atual": "efetivo_atual",
    "T.C. Anterior": "tc_anterior",
    "T.C. Atual": "tc_atual",
    "MIX": "mix",
    "1º Mês": "volume_mes_1",
    "2º Mês": "volume_mes_2",
    "3º Mês": "volume_mes_3",
    "4º Mês": "volume_mes_4",
    "% Ganho": "percentual_ganho",
    "Custo Par Anterior": "custo_par_anterior",
    "Custo Par Atual": "custo_par_atual",
}

NUMERIC_COLUMNS = [
    "preco_mp",
    "consumo_anterior",
    "consumo_atual",
    "padrao_anterior",
    "padrao_atual",
    "efetivo_anterior",
    "efetivo_atual",
    "tc_anterior",
    "tc_atual",
    "mix",
    "volume_mes_1",
    "volume_mes_2",
    "volume_mes_3",
    "volume_mes_4",
    "percentual_ganho",
    "custo_par_anterior",
    "custo_par_atual",
]

# numero da linha no Excel: cabecalho na linha 1, dados a partir da 2
EXCEL_FIRST_DATA_ROW = 2

MAX_ERRORS_REPORTED = 30

_FAP_PATTERN = re.compile(r"^\d{10,20}$")


class SpreadsheetError(ValueError):
    """Planilha com formato invalido. A mensagem lista os problemas encontrados."""


@dataclass(frozen=True)
class SpreadsheetData:
    rows: pd.DataFrame
    sheet_name: str
    empty_rows_dropped: int


def normalize_code(value: object) -> str | None:
    """Converte codigo lido do Excel em texto, sem o '.0' que celula numerica traz."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return re.sub(r"\.0+$", "", text)


def parse_fap_list(raw: str | list[str] | None) -> list[str]:
    """Aceita FAPs separadas por virgula, ponto e virgula, espaco ou quebra de linha."""
    if not raw:
        return []
    items = raw if isinstance(raw, list) else re.split(r"[\s,;]+", raw)
    faps = [code for code in (normalize_code(item) for item in items) if code]
    return sorted(set(faps))


def resolve_sheet_name(path: Path, sheet_name: str | None) -> str:
    # sem fallback para a primeira aba: planilhas reais trazem uma aba de historico
    # na frente e importar a aba errada e facil
    sheets = pd.ExcelFile(path, engine="openpyxl").sheet_names
    if not sheet_name:
        raise SpreadsheetError(f"Informe a aba da planilha. Abas disponiveis: {sheets}")
    if sheet_name not in sheets:
        raise SpreadsheetError(
            f"Aba '{sheet_name}' nao existe na planilha. Abas disponiveis: {sheets}"
        )
    return sheet_name


def _check_columns(df: pd.DataFrame) -> None:
    missing = [col for col in COLUMN_MAP if col not in df.columns]
    if missing:
        raise SpreadsheetError(
            f"Colunas obrigatorias ausentes na planilha: {missing}. Encontradas: {list(df.columns)}"
        )


def _format_errors(errors: list[str]) -> str:
    shown = errors[:MAX_ERRORS_REPORTED]
    extra = len(errors) - len(shown)
    suffix = f"\n... e mais {extra} erro(s)" if extra > 0 else ""
    return "\n".join(shown) + suffix


def _coerce_numeric(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    errors: list[str] = []
    converted = {}
    for col in NUMERIC_COLUMNS:
        parsed = pd.to_numeric(df[col], errors="coerce")
        invalid = parsed.isna() & df[col].notna()
        errors.extend(
            f"linha {line}: '{col}' nao numerico ({value!r})"
            for line, value in zip(df.loc[invalid, "linha"], df.loc[invalid, col], strict=True)
        )
        converted[col] = parsed
    return df.assign(**converted), errors


def _duplicate_errors(df: pd.DataFrame) -> list[str]:
    """Linhas identicas em todas as colunas somariam o mesmo ganho mais de uma vez."""
    business_cols = [col for col in df.columns if col != "linha"]
    dup = df.loc[df.duplicated(subset=business_cols, keep=False)]
    if dup.empty:
        return []
    groups = dup.groupby(business_cols, dropna=False, sort=False)
    return [
        f"{groups.ngroups} grupo(s) de linhas duplicadas ({len(dup)} linhas com todas as "
        "colunas iguais). Corrija a planilha removendo as repeticoes e envie de novo:",
        *(
            f"linhas {', '.join(map(str, group['linha']))}: "
            f"FAP {group['numero_fap'].iat[0]}, Código {group['cod_prod'].iat[0]}"
            for _, group in groups
        ),
    ]


def normalize(raw: pd.DataFrame, faps: list[str]) -> tuple[pd.DataFrame, int]:
    """Renomeia, tipa e filtra a planilha crua. Retorna (linhas, linhas vazias descartadas)."""
    renamed = raw.rename(columns=lambda col: str(col).strip())
    _check_columns(renamed)

    df = (
        renamed[list(COLUMN_MAP)]
        .rename(columns=COLUMN_MAP)
        .assign(linha=range(EXCEL_FIRST_DATA_ROW, EXCEL_FIRST_DATA_ROW + len(renamed)))
    )
    df = df.assign(
        **{col: df[col].map(normalize_code) for col in ("numero_fap", "cod_prod")},
        **{
            col: df[col].map(lambda v: str(v).strip() if pd.notna(v) else None)
            for col in ("tipo_melhoria", "filial", "setor", "nome_solicitante")
        },
    )

    empty = df["numero_fap"].isna()
    df = df.loc[~empty]
    if faps:
        df = df.loc[df["numero_fap"].isin(faps)]

    errors: list[str] = []
    missing_faps = sorted(set(faps) - set(df["numero_fap"]))
    if missing_faps:
        errors.append(f"FAP(s) informada(s) sem linhas na planilha: {missing_faps}")
    if df.empty and not missing_faps:
        errors.append("Nenhuma linha com 'Nº F.A.P' preenchido na planilha.")

    bad_fap = ~df["numero_fap"].str.match(_FAP_PATTERN)
    errors.extend(
        f"linha {line}: 'Nº F.A.P' invalido ({value!r})"
        for line, value in zip(df.loc[bad_fap, "linha"], df.loc[bad_fap, "numero_fap"], strict=True)
    )
    errors.extend(
        f"linha {line}: 'Código' vazio" for line in df.loc[df["cod_prod"].isna(), "linha"]
    )

    dt_fap = pd.to_datetime(df["dt_fap"], errors="coerce", dayfirst=True)
    errors.extend(
        f"linha {line}: 'Data da FAP' invalida ({value!r})"
        for line, value in zip(
            df.loc[dt_fap.isna() & df["dt_fap"].notna(), "linha"],
            df.loc[dt_fap.isna() & df["dt_fap"].notna(), "dt_fap"],
            strict=True,
        )
    )
    df = df.assign(dt_fap=dt_fap.dt.normalize())

    df, numeric_errors = _coerce_numeric(df)
    errors.extend(numeric_errors)

    # so depois de tipar: '1' e 1.0 precisam contar como o mesmo valor
    if not errors:
        errors.extend(_duplicate_errors(df))

    if errors:
        raise SpreadsheetError("Planilha invalida:\n" + _format_errors(errors))

    return df.reset_index(drop=True), int(empty.sum())


def read_spreadsheet(path: Path, sheet_name: str | None, faps: list[str]) -> SpreadsheetData:
    if not path.exists():
        raise SpreadsheetError(f"Arquivo nao encontrado: {path}")

    sheet = resolve_sheet_name(path, sheet_name)
    raw = pd.read_excel(
        path,
        sheet_name=sheet,
        engine="openpyxl",
        # texto para nao perder zero a esquerda do codigo nem virar notacao cientifica na FAP
        dtype={"Nº F.A.P": str, "Código": str},
    )
    try:
        rows, empty_dropped = normalize(raw, faps)
    except SpreadsheetError as exc:
        raise SpreadsheetError(f"Aba '{sheet}': {exc}") from exc
    return SpreadsheetData(rows=rows, sheet_name=sheet, empty_rows_dropped=empty_dropped)
