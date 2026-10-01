"""Testes da resolução de datas do SharePoint (dd/MM vs MM/dd + fuso)."""

import pandas as pd
import pytest
from global_modules.sharepoint.datetime_resolve import (
    DatetimeConfig,
    resolve_datetimes,
    resolve_with_config,
)

# Âncora (já em hora local BR naive) equivalente ao ID 107236.
CREATED_BR = pd.Timestamp("2026-06-03 16:59:40")  # 19:59:40Z - 3h
MODIFIED_BR = pd.Timestamp("2026-06-03 17:05:33")  # 20:05:33Z - 3h


def _resolve_one(raw, source_tz, created=CREATED_BR, modified=MODIFIED_BR):
    col = "dt"
    df = pd.DataFrame({col: [raw], "Created": [created], "Modified": [modified]})
    local = [col] if source_tz == "local" else []
    utc = [col] if source_tz == "utc" else []
    out = resolve_datetimes(df, local, utc, system_fields=[])
    return out[col].iloc[0]


def test_ddmm_ambiguo_resolvido_pela_ancora():
    # "03/06/2026" -> dd/MM=3 jun (na janela), MM/dd=6 mar (fora) -> 3 jun.
    assert _resolve_one("03/06/2026 17:05:32", "local") == pd.Timestamp("2026-06-03 17:05:32")


def test_mmdd_utc_resolvido_e_convertido_para_br():
    # analista: "06/03/2026 20:00:34" em UTC -> 3 jun 17:00:34 BR.
    assert _resolve_one("06/03/2026 20:00:34", "utc") == pd.Timestamp("2026-06-03 17:00:34")


def test_dia_maior_que_12_nao_e_ambiguo():
    # "15/06/2026" só faz sentido como dd/MM.
    assert _resolve_one("15/06/2026 10:00:00", "local") == pd.Timestamp("2026-06-15 10:00:00")


def test_ddmm_12_02_ambiguo_resolve_para_fevereiro():
    # Regressão FAP 133102026020401: cru "12/02/2026" (12 fev) era gravado como
    # 2026-12-02 pelo parse legado month-first (pd.to_datetime dayfirst=False).
    # A âncora de fevereiro (Created 04/fev, Modified 12/fev) deve fixar 12 fev.
    created = pd.Timestamp("2026-02-04 12:04:18")
    modified = pd.Timestamp("2026-02-12 19:39:17")
    got = _resolve_one("12/02/2026 16:39:16", "local", created=created, modified=modified)
    assert got == pd.Timestamp("2026-02-12 16:39:16")


def test_ddmm_12_02_sem_ancora_vence_intencao_dayfirst():
    # Sem âncora, o ambíguo cai na intenção dd/MM do PA -> 12 fev, nunca 2 dez.
    got = _resolve_one("12/02/2026 16:39:16", "local", created=pd.NaT, modified=pd.NaT)
    assert got == pd.Timestamp("2026-02-12 16:39:16")


def test_mes_na_primeira_posicao_invalido_como_ddmm():
    # "06/15/2026": dd/MM inválido (mês 15) -> MM/dd = 15 jun.
    assert _resolve_one("06/15/2026 10:00:00", "local") == pd.Timestamp("2026-06-15 10:00:00")


def test_fallback_ddmm_sem_ancora():
    # Sem Created/Modified, ambíguo cai na intenção do PA (dd/MM).
    got = _resolve_one("03/06/2026 16:59:48", "local", created=pd.NaT, modified=pd.NaT)
    assert got == pd.Timestamp("2026-06-03 16:59:48")


def test_vazio_vira_nat():
    for raw in [None, "", "nan", "None"]:
        assert pd.isna(_resolve_one(raw, "local"))


def test_system_field_iso_utc_para_br_naive():
    df = pd.DataFrame({"Created": ["2026-06-03T19:59:40Z"], "Modified": ["2026-06-03T20:05:33Z"]})
    out = resolve_datetimes(df, [], [], system_fields=["Created", "Modified"])
    assert out["Created"].iloc[0] == pd.Timestamp("2026-06-03 16:59:40")
    assert out["Modified"].iloc[0] == pd.Timestamp("2026-06-03 17:05:33")


def test_end_to_end_id_107236():
    df = pd.DataFrame({
        "dt_aprovacao_eng": ["03/06/2026 17:05:32"],
        "dt_aprovacao_producao": ["03/06/2026 17:05:29"],
        "dt_inicio_fluxo": ["03/06/2026 16:59:48"],
        "dt_aprovacao_analista": ["06/03/2026 20:00:34"],
        "Created": ["2026-06-03T19:59:40Z"],
        "Modified": ["2026-06-03T20:05:33Z"],
    })
    config = DatetimeConfig(
        event_local_fields=["dt_aprovacao_eng", "dt_aprovacao_producao", "dt_inicio_fluxo"],
        event_utc_fields=["dt_aprovacao_analista"],
        system_fields=["Created", "Modified"],
    )
    out = resolve_with_config(df, config).iloc[0]

    assert out["dt_aprovacao_eng"] == pd.Timestamp("2026-06-03 17:05:32")
    assert out["dt_aprovacao_producao"] == pd.Timestamp("2026-06-03 17:05:29")
    assert out["dt_inicio_fluxo"] == pd.Timestamp("2026-06-03 16:59:48")
    assert out["dt_aprovacao_analista"] == pd.Timestamp("2026-06-03 17:00:34")
    assert out["Created"] == pd.Timestamp("2026-06-03 16:59:40")
    assert out["Modified"] == pd.Timestamp("2026-06-03 17:05:33")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("31/12/2025 23:59:59", pd.Timestamp("2025-12-31 23:59:59")),
        ("01/01/2026", pd.Timestamp("2026-01-01 00:00:00")),
    ],
)
def test_manual_dayfirst(raw, expected):
    df = pd.DataFrame({"dt_fap": [raw]})
    out = resolve_datetimes(df, [], [], system_fields=[], manual_fields=["dt_fap"])
    assert out["dt_fap"].iloc[0] == expected
