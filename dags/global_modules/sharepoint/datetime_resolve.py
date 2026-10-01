"""Resolução determinística de datas vindas do SharePoint.

O Power Automate alimenta a lista de aprovações de formas inconsistentes:

- A maioria dos campos vem como texto ``dd/MM/yyyy HH:mm:ss`` em hora local BR
  (``convertFromUtc(..., 'E. South America Standard Time', 'dd/MM/yyyy HH:mm:ss')``),
  mas às vezes o flow erra e manda ``MM/dd/yyyy``.
- ``dt_aprovacao_analista`` vem do ``powerautomate.approvals.responseDate``, que é
  sempre UTC.
- ``Created`` / ``Modified`` são campos de sistema do SharePoint e chegam em ISO-UTC.

A inferência automática do pandas (``pd.to_datetime`` sem ``format``) troca dia/mês
quando o dia é <= 12, gravando, por exemplo, ``03/06/2026`` (3 de junho) como
``2026-03-06`` (6 de março). Este módulo resolve isso:

- O fuso é fixado pela categoria do campo (não é adivinhado).
- O formato (``dd/MM`` vs ``MM/dd``) é desambiguado usando ``Created``/``Modified``
  como âncora temporal: todo evento de aprovação ocorre dentro da vida do item.

Todas as colunas resultantes ficam em hora local de ``America/Fortaleza`` (naive).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

BR_TZ = ZoneInfo("America/Fortaleza")
ANCHOR_TOLERANCE = timedelta(days=2)
ANCHOR_CREATED = "Created"
ANCHOR_MODIFIED = "Modified"
_MAX_MONTH = 12
_MAX_DAY = 31


@dataclass(frozen=True)
class DatetimeConfig:
    """Categoriza as colunas de data de uma lista do SharePoint para resolução.

    :param event_local_fields: eventos em hora local BR (`convertFromUtc`).
    :param event_utc_fields: eventos em UTC (ex.: `responseDate`).
    :param system_fields: campos de sistema em ISO-UTC (`Created`, `Modified`); âncora.
    :param manual_fields: datas preenchidas manualmente (dd/MM, sem âncora).
    """

    event_local_fields: list[str] = field(default_factory=list)
    event_utc_fields: list[str] = field(default_factory=list)
    system_fields: list[str] = field(default_factory=list)
    manual_fields: list[str] = field(default_factory=list)

    @property
    def all_fields(self) -> list[str]:
        return [
            *self.event_local_fields,
            *self.event_utc_fields,
            *self.system_fields,
            *self.manual_fields,
        ]


# "03/06/2026 17:05:32", "03/06/2026" ou separador 'T'
_SLASH_DT = re.compile(
    r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*$"
)
_EMPTY = {"", "nan", "none", "nat", "null"}


def _is_empty(raw) -> bool:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return True
    return isinstance(raw, str) and raw.strip().lower() in _EMPTY


def _to_br_naive(naive_local: datetime, source_tz: str) -> datetime:
    """Converte um `datetime` naive (parseado do texto) para hora local BR naive."""
    if source_tz == "utc":
        return naive_local.replace(tzinfo=timezone.utc).astimezone(BR_TZ).replace(tzinfo=None)
    # source_tz == "local": já está em hora local BR
    return naive_local


def _candidates(a: int, b: int, year: int, time: tuple[int, int, int], source_tz: str):
    """Gera candidatos (nome, datetime_br_naive) válidos para as interpretações de data."""
    h, m, s = time
    out = []
    for day, month, name in ((a, b, "ddmm"), (b, a, "mmdd")):
        if not (1 <= month <= _MAX_MONTH and 1 <= day <= _MAX_DAY):
            continue
        try:
            naive = datetime(year, month, day, h, m, s)
        except ValueError:
            continue  # ex.: 31 de fevereiro
        br = _to_br_naive(naive, source_tz)
        if all(name != n for n, _ in out):
            out.append((name, br))
    return out


def _pick(cands, created, modified):
    """Escolhe o candidato pela âncora; fallback para dd/MM."""
    if not cands:
        return pd.NaT
    if len(cands) == 1:
        return cands[0][1]

    lo = created - ANCHOR_TOLERANCE if pd.notna(created) else None
    hi = modified + ANCHOR_TOLERANCE if pd.notna(modified) else None

    def _in_window(dt: datetime) -> bool:
        if lo is not None and dt < lo:
            return False
        if hi is not None and dt > hi:
            return False
        return True

    in_window = [c for c in cands if _in_window(c[1])]
    if len(in_window) == 1:
        return in_window[0][1]

    # Empate (ambos na janela) ou nenhum: cai na intenção documentada do PA (dd/MM).
    for name, dt in cands:
        if name == "ddmm":
            return dt
    return cands[0][1]


def _resolve_value(raw, created, modified, source_tz: str):
    if _is_empty(raw):
        return pd.NaT

    match = _SLASH_DT.match(str(raw))
    if match is None:
        # Não é o formato esperado: tenta ISO-ish como último recurso.
        return pd.to_datetime(raw, errors="coerce")

    a, b, year = int(match[1]), int(match[2]), int(match[3])
    h = int(match[4]) if match[4] else 0
    m = int(match[5]) if match[5] else 0
    s = int(match[6]) if match[6] else 0

    cands = _candidates(a, b, year, (h, m, s), source_tz)
    return _pick(cands, created, modified)


def _parse_iso_utc_to_br(series: pd.Series) -> pd.Series:
    """Campos de sistema (ISO-UTC) -> hora local BR naive."""
    parsed = pd.to_datetime(series, utc=True, errors="coerce")
    return parsed.dt.tz_convert(BR_TZ).dt.tz_localize(None)


def _parse_manual(series: pd.Series) -> pd.Series:
    """Datas preenchidas manualmente (sem âncora): assume dd/MM em hora local."""
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def _resolve_event(
    series: pd.Series,
    created: pd.Series,
    modified: pd.Series,
    source_tz: str,
) -> pd.Series:
    values = [
        _resolve_value(raw, created.iloc[i], modified.iloc[i], source_tz)
        for i, raw in enumerate(series)
    ]
    return pd.to_datetime(pd.Series(values, index=series.index), errors="coerce")


def resolve_datetimes(
    df: pd.DataFrame,
    event_local_fields: list[str],
    event_utc_fields: list[str],
    system_fields: list[str],
    manual_fields: list[str] | None = None,
) -> pd.DataFrame:
    """Normaliza as colunas de data para hora local BR (naive), resolvendo a ambiguidade
    dd/MM vs MM/dd via âncora ``Created``/``Modified``.

    :param df: DataFrame com as colunas de data ainda como `str` (cru do SharePoint).
    :param event_local_fields: campos de evento em hora local BR (`convertFromUtc`).
    :param event_utc_fields: campos de evento em UTC (ex.: `responseDate`).
    :param system_fields: campos de sistema em ISO-UTC (`Created`, `Modified`); são a âncora.
    :param manual_fields: campos de data preenchidos manualmente (dd/MM, sem âncora).
    :return: novo DataFrame com as colunas de data como `datetime64[ns]` naive em hora BR.
    """
    df = df.copy()

    for col in system_fields:
        if col in df.columns:
            df[col] = _parse_iso_utc_to_br(df[col])

    nat = pd.Series(pd.NaT, index=df.index)
    created = df[ANCHOR_CREATED] if ANCHOR_CREATED in df.columns else nat
    modified = df[ANCHOR_MODIFIED] if ANCHOR_MODIFIED in df.columns else nat

    for col in event_local_fields:
        if col in df.columns:
            df[col] = _resolve_event(df[col], created, modified, "local")

    for col in event_utc_fields:
        if col in df.columns:
            df[col] = _resolve_event(df[col], created, modified, "utc")

    for col in manual_fields or []:
        if col in df.columns:
            df[col] = _parse_manual(df[col])

    return df


def resolve_with_config(df: pd.DataFrame, config: DatetimeConfig) -> pd.DataFrame:
    """Atalho de `resolve_datetimes` a partir de um `DatetimeConfig`."""
    return resolve_datetimes(
        df,
        event_local_fields=config.event_local_fields,
        event_utc_fields=config.event_utc_fields,
        system_fields=config.system_fields,
        manual_fields=config.manual_fields,
    )
