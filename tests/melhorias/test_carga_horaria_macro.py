"""Testes da geracao da carga de mel_carga_horaria_macro a partir da planilha do Qlik."""

from datetime import datetime

import pandas as pd
import pytest
from melhorias.scripts.carga_horaria_macro import (
    CargaHorariaError,
    normalize,
    render_sql,
)


def _linha(**overrides) -> dict[str, object]:
    defaults = {
        "Area": "Montagem",
        "Ch": 16.35,
        "Qtde turnos": 2.0,
        "dias": 21.0,
        "h/mês/Func": 171.675,
        "mes": 1,
        "mes ano": "jan/2015",
        "data": datetime(2015, 1, 1),
        "estabelecimento": "Fortaleza",
    }
    return {**defaults, **overrides}


def _planilha(*linhas):
    return pd.DataFrame(list(linhas))


def test_normalize_seleciona_e_renomeia_colunas():
    out = normalize(_planilha(_linha()))

    assert list(out.columns) == ["estabelecimento", "area", "mes", "ch_mensal"]
    assert out.iloc[0].to_dict() == {
        "estabelecimento": "Fortaleza",
        "area": "Montagem",
        "mes": pd.Timestamp(2015, 1, 1),
        "ch_mensal": 171.675,
    }


def test_normalize_remove_espacos_e_trunca_data_no_inicio_do_mes():
    out = normalize(
        _planilha(_linha(Area=" Injeção ", estabelecimento="Crato ", data=datetime(2021, 3, 15)))
    )

    row = out.iloc[0]
    assert (row.estabelecimento, row.area, row.mes) == (
        "Crato",
        "Injeção",
        pd.Timestamp(2021, 3, 1),
    )


def test_normalize_descarta_duplicata_exata():
    out = normalize(_planilha(_linha(), _linha()))

    assert len(out) == 1


def test_normalize_falha_em_chave_com_valores_diferentes():
    planilha = _planilha(
        _linha(**{"Area": "Demais Processos", "estabelecimento": "Sobral", "h/mês/Func": 154.8}),
        _linha(**{"Area": "Demais Processos", "estabelecimento": "Sobral", "h/mês/Func": 189.2}),
    )

    with pytest.raises(CargaHorariaError, match="Sobral.*Demais Processos.*2015-01"):
        normalize(planilha)


@pytest.mark.parametrize("valor", [0.0, -1.0, None])
def test_normalize_falha_em_carga_nula_ou_nao_positiva(valor):
    with pytest.raises(CargaHorariaError, match="h/mês/Func"):
        normalize(_planilha(_linha(**{"h/mês/Func": valor})))


def test_normalize_falha_sem_coluna_obrigatoria():
    planilha = _planilha(_linha()).drop(columns="Area")

    with pytest.raises(CargaHorariaError, match="Area"):
        normalize(planilha)


def test_normalize_ordena_pela_chave():
    out = normalize(
        _planilha(
            _linha(estabelecimento="Sobral", data=datetime(2021, 2, 1)),
            _linha(estabelecimento="Crato", data=datetime(2021, 2, 1)),
            _linha(estabelecimento="Crato", data=datetime(2021, 1, 1)),
        )
    )

    assert list(zip(out.estabelecimento, out.mes.dt.month)) == [
        ("Crato", 1),
        ("Crato", 2),
        ("Sobral", 2),
    ]


def _normalizado(n):
    return pd.DataFrame({
        "estabelecimento": ["Crato"] * n,
        "area": [f"Area {i}" for i in range(n)],
        "mes": [pd.Timestamp(2021, 1, 1)] * n,
        "ch_mensal": [171.675] * n,
    })


def test_render_sql_recarrega_a_tabela_numa_transacao():
    sql = render_sql(_normalizado(1))

    assert "create table dbo.mel_carga_horaria_macro" in sql
    assert sql.index("begin transaction") < sql.index("delete from dbo.mel_carga_horaria_macro")
    assert sql.index("delete from") < sql.index("insert into") < sql.index("commit")
    assert "(N'Crato', N'Area 0', '2021-01-01', 171.675)" in sql


def test_render_sql_escapa_aspas():
    df = _normalizado(1).assign(area="Pré'Montagem")

    assert "N'Pré''Montagem'" in render_sql(df)


def test_render_sql_quebra_insert_em_lotes_de_1000_linhas():
    lotes_esperados = 3  # 1000 + 1000 + 1

    sql = render_sql(_normalizado(2001))

    assert sql.count("insert into dbo.mel_carga_horaria_macro") == lotes_esperados
