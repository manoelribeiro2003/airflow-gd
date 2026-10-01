"""Testes da geracao do SQL de carga de FAPs aprovadas que ficaram fora de mel_aprovacao."""

import datetime as dt

import pandas as pd
import pytest
from melhorias.scripts.aprovacao_planilha import (
    AprovacaoPlanilhaError,
    render_sql,
    select_rows,
)

FAP = "193102021022501"


def _aprovacao(**campos):
    base = {
        "ID": [5326],
        "numero_fap": [FAP],
        "status": ["Aprovado"],
        "dt_fap": [pd.NaT],
        "tipo_melhoria": [None],
        "cracha_idealizador": [float("nan")],
        "Created": [pd.Timestamp("2021-02-25 10:00:01.5")],
    }
    return pd.DataFrame({**base, **campos})


def _planilha(dt_planilha: dt.date | None = dt.date(2021, 2, 26), tipo="FAO"):
    return pd.DataFrame({
        "numero_fap": [FAP],
        "dt_planilha": [dt_planilha],
        "tipo_planilha": [tipo],
    })


def test_select_rows_usa_data_e_tipo_da_planilha():
    out = select_rows(_aprovacao(), _planilha())

    assert out.dt_fap.tolist() == [pd.Timestamp("2021-02-26")]
    assert out.tipo_melhoria.tolist() == ["FAO"]
    assert list(out.columns) == list(_aprovacao().columns)


def test_select_rows_mantem_tipo_da_aprovacao():
    out = select_rows(_aprovacao(tipo_melhoria=["Manutenção"]), _planilha())

    assert out.tipo_melhoria.tolist() == ["Manutenção"]


def test_select_rows_sem_data_na_planilha_fica_a_da_linha():
    linha = _aprovacao(dt_fap=[pd.Timestamp("2021-01-04")])

    out = select_rows(linha, _planilha(dt_planilha=None))

    assert out.dt_fap.tolist() == [pd.Timestamp("2021-01-04")]


def test_select_rows_descarta_fap_sem_data():
    assert select_rows(_aprovacao(), _planilha(dt_planilha=None)).empty


def test_select_rows_so_aprovado_e_lancado_na_planilha():
    reprovada = _aprovacao(status=["Reprovado"])
    fora = _aprovacao(numero_fap=["99999999999999"])

    assert select_rows(reprovada, _planilha()).empty
    assert select_rows(fora, _planilha()).empty


def test_select_rows_falha_com_fap_repetida():
    dup = pd.concat([_aprovacao(), _aprovacao(ID=[5327])], ignore_index=True)

    with pytest.raises(AprovacaoPlanilhaError):
        select_rows(dup, _planilha())


def test_render_sql_trava_e_literais():
    sql = render_sql(select_rows(_aprovacao(), _planilha()))

    assert sql.startswith("set xact_abort on;\nbegin transaction;")
    assert f"where ID in (5326) or numero_fap in (N'{FAP}')" in sql
    assert "throw 50003" in sql
    assert "insert into dbo.mel_aprovacao ([ID], [numero_fap], [status], [dt_fap]" in sql
    assert (
        f"(5326, N'{FAP}', N'Aprovado', '2021-02-26T00:00:00.000', N'FAO', null, "
        "'2021-02-25T10:00:01.500')"
    ) in sql
    assert sql.rstrip().endswith("commit;")
