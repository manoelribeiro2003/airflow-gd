"""Testes da normalizacao da planilha de ganhos importada manualmente."""

from datetime import datetime

import pandas as pd
import pytest
from melhorias.dags.MANUAL_MELHORIAS_GANHOS_PLANILHA.spreadsheet import (
    COLUMN_MAP,
    SpreadsheetError,
    normalize,
    normalize_code,
    parse_fap_list,
)


def _linha(**overrides) -> dict[str, object]:
    defaults = {
        "Tipo de Melhoria": "Tempo Ciclo",
        "Estab.": "Sobral",
        "Setor": "Fábrica 01",
        "Processista": "Fulano",
        "Nº F.A.P": "01032026082901",
        "Data da FAP": datetime(2026, 9, 1),
        "Código": "11578",
    }
    return {**dict.fromkeys(COLUMN_MAP, 0.0), **defaults, **overrides}


def _planilha(*linhas):
    # cabecalhos reais da planilha tem espacos sobrando (' Setor', 'Padrão Anterior ')
    df = pd.DataFrame(list(linhas))
    return df.rename(columns={"Setor": " Setor", "Padrão Anterior": "Padrão Anterior "})


def test_normalize_code_remove_sufixo_de_celula_numerica():
    assert normalize_code("14032026091901.0") == "14032026091901"
    assert normalize_code(" 05320 ") == "05320"
    assert normalize_code(None) is None
    assert normalize_code(float("nan")) is None


def test_parse_fap_list_aceita_varios_separadores_e_remove_duplicadas():
    assert parse_fap_list("02, 01;03\n01") == ["01", "02", "03"]
    assert parse_fap_list("") == []
    assert parse_fap_list(None) == []


def test_normalize_mapeia_colunas_e_numera_linha_do_excel():
    rows, vazias = normalize(_planilha(_linha(), _linha(**{"Código": "11592"})), faps=[])

    assert vazias == 0
    assert list(rows["cod_prod"]) == ["11578", "11592"]
    assert list(rows["linha"]) == [2, 3]
    assert rows.loc[0, "setor"] == "Fábrica 01"
    assert "padrao_anterior" in rows.columns


def test_normalize_descarta_linhas_sem_fap():
    rows, vazias = normalize(_planilha(_linha(), _linha(**{"Nº F.A.P": None})), faps=[])

    assert len(rows) == 1
    assert vazias == 1


def test_normalize_filtra_pelas_faps_informadas():
    planilha = _planilha(_linha(), _linha(**{"Nº F.A.P": "22032026082901"}))

    rows, _ = normalize(planilha, faps=["22032026082901"])

    assert list(rows["numero_fap"]) == ["22032026082901"]


def test_normalize_falha_quando_fap_informada_nao_esta_na_planilha():
    with pytest.raises(SpreadsheetError, match="99999999999999"):
        normalize(_planilha(_linha()), faps=["99999999999999"])


def test_normalize_falha_com_coluna_obrigatoria_ausente():
    with pytest.raises(SpreadsheetError, match="MIX"):
        normalize(_planilha(_linha()).drop(columns=["MIX"]), faps=[])


def test_normalize_aponta_linha_com_valor_nao_numerico():
    with pytest.raises(SpreadsheetError, match="linha 3: 'mix'"):
        normalize(_planilha(_linha(), _linha(MIX="abc")), faps=[])


def test_normalize_aponta_codigo_vazio():
    with pytest.raises(SpreadsheetError, match="linha 2: 'Código' vazio"):
        normalize(_planilha(_linha(**{"Código": None})), faps=[])


def test_normalize_rejeita_linhas_duplicadas_e_aponta_as_linhas():
    planilha = _planilha(_linha(), _linha(**{"Código": "11592"}), _linha())

    with pytest.raises(SpreadsheetError, match=r"linhas 2, 4: FAP 01032026082901, Código 11578"):
        normalize(planilha, faps=[])


def test_normalize_aceita_mesmo_codigo_com_valores_diferentes():
    rows, _ = normalize(_planilha(_linha(MIX=30.9), _linha(MIX=13.61)), faps=[])

    assert list(rows["mix"]) == [30.9, 13.61]
