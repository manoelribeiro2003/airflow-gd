"""Testes da geracao da carga de mel_ganhos_hist a partir das planilhas do Qlik."""

import datetime as dt

import pandas as pd
import pytest
from melhorias.scripts.ganhos_hist import (
    COLUMNS,
    FONTE_PLANILHA_SEED,
    GanhosHistError,
    main,
    normalize,
    parse_ganho,
    read_faps,
    render_sql,
)
from melhorias.scripts.volume_real_hist import SEM_CODIGO

NORMAL_2021 = "BASE_LANC_MELHORIAS_2021_Sobral.app.1.xlsx"
NORMAL_2024 = "BASE_LANC_MELHORIAS_2024_Sobral.app.1.xlsx"
NORMAL_2025 = "BASE_LANC_MELHORIAS_2025_Sobral.app.2.xlsx"
ANTERIOR_2021 = "BASE_LANC_MELHORIAS_2021_Sobral.app.mês.anterior.xlsx"
FAP = "23032021010404"


def _linha(
    arquivo: str = NORMAL_2021,
    fap: object = FAP,
    cod: object = "0224374",
    tipo: object = "Tempo Ciclo",
    campos: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "arquivo": arquivo,
        "Tipo de Melhoria": tipo,
        "Estab.": "Sobral",
        "Setor": "Plastisol",
        "Nº F.A.P": fap,
        "Data da FAP": dt.datetime(2021, 1, 1),
        "Código": cod,
        "Preço M.P.": 12.5,
        "Cons_Anterior": 0.3,
        "Cons_Atual": 0.25,
        "T.C. Anterior": 10.0,
        "T.C. Atual": 8.0,
        "MIX": 46.0,
        "Custo Par Anterior": 1.2,
        "Custo Par Atual": 1.1,
        "Ganho mês R$": "40286,88",
        "Origem": "TC / MP",
        "Setor Macro": "Montagem",
        "Idealizador": "Ana",
        "Gerente idealizador": "Beatriz",
        "É replicação": "Não",
        "Cargo": "Analista de Processos",
        "cracha": "13783497",
        **(campos or {}),
    }


def _planilha(*linhas):
    return pd.DataFrame(list(linhas))


def test_normalize_mapeia_colunas_da_planilha_para_o_contrato_de_mel_ganhos():
    out = normalize(_planilha(_linha()), {FAP})
    row = out.iloc[0].to_dict()

    assert list(out.columns) == COLUMNS
    assert pd.isna(row.pop("ganho_previsto"))
    assert {"ganho_previsto": None, **row} == {
        "id": 1,
        "numero_fap": FAP,
        "cod_prod": "224374",
        "dt_fap": dt.date(2021, 1, 1),
        "tipo_melhoria": "Tempo Ciclo",
        "filial": "Sobral",
        "setor": "Plastisol",
        "macro_setor": "Montagem",
        "tc_anterior": 10.0,
        "tc_atual": 8.0,
        "mix": 46.0,
        "consumo_anterior": 0.3,
        "consumo_atual": 0.25,
        "preco_mp": 12.5,
        "custo_par_anterior": 1.2,
        "custo_par_atual": 1.1,
        "ganho_previsto": None,
        "cracha_idealizador": 13783497,
        "nome_idealizador": "Ana",
        "gerente_idealizador": "Beatriz",
        "cargo": "Analista de Processos",
        "origem_melhoria": "TC / MP",
        "replicacao": "Não",
        "arquivo_origem": NORMAL_2021,
    }


def test_normalize_so_leva_faps_da_lista():
    # a lista e o export das FAPs aprovadas sem nenhuma linha em mel_ganhos
    out = normalize(_planilha(_linha(fap="A"), _linha(fap="B")), {"B"})

    assert out.numero_fap.tolist() == ["B"]


def test_normalize_remove_espacos_da_fap_antes_de_casar_com_a_lista():
    out = normalize(_planilha(_linha(fap=f" {FAP} ")), {FAP})

    assert out.numero_fap.tolist() == [FAP]


@pytest.mark.parametrize(
    "tipo", ["Tempo Ciclo", "Aglutinação", "Consumo", "Troca de Matéria Prima"]
)
def test_normalize_leva_os_quatro_tipos_de_ganho_por_volume(tipo):
    assert len(normalize(_planilha(_linha(tipo=tipo)), {FAP})) == 1


def test_normalize_tipo_com_volume_nao_leva_ganho_da_planilha():
    # o ganho sai do volume real (int_ganhos_calc); a planilha nao tem volume previsto
    assert normalize(_planilha(_linha()), {FAP}).ganho_previsto.isna().all()


@pytest.mark.parametrize("tipo", ["Acondicionamento", "FAO", "Logística externa"])
def test_normalize_demais_tipos_levam_ganho_mes_como_ganho_previsto(tipo):
    out = normalize(_planilha(_linha(tipo=tipo)), {FAP})

    assert out.tipo_melhoria.tolist() == [tipo]
    assert out.ganho_previsto.tolist() == [40286.88]


def test_normalize_demais_tipos_sem_codigo_ficam():
    # o ganho e da FAP; mel_ganhos tambem nao tem codigo nesses tipos
    out = normalize(_planilha(_linha(tipo="FAO", cod=None)), {FAP})

    assert out.cod_prod.tolist() == [None]
    assert out.ganho_previsto.tolist() == [40286.88]


def test_normalize_demais_tipos_uma_linha_por_fap():
    # a planilha repete a linha em algumas FAPs e o Qlik somava o ganho em dobro
    out = normalize(_planilha(_linha(tipo="FAO", cod=None), _linha(tipo="FAO", cod=None)), {FAP})

    assert out.id.tolist() == [1]
    assert out.ganho_previsto.tolist() == [40286.88]


def test_normalize_demais_tipos_soma_ganhos_diferentes_na_fap():
    # FAO de 2021 com um lancamento por posto: ganhos diferentes somam; o repetido nao
    linhas = [
        _linha(tipo="FAO", cod=None, campos={"Ganho mês R$": "1,5"}),
        _linha(tipo="FAO", cod=None, campos={"Ganho mês R$": "2,5"}),
        _linha(tipo="FAO", cod=None, campos={"Ganho mês R$": "2,5"}),
    ]

    out = normalize(_planilha(*linhas), {FAP})

    assert out.id.tolist() == [1]
    assert out.ganho_previsto.tolist() == [4.0]


def test_normalize_descarta_linha_sem_tipo():
    assert normalize(_planilha(_linha(tipo=None)), {FAP}).empty


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("0,01", 0.01),
        ("40286,88", 40286.88),
        ("-0,27", -0.27),
        (" 12 ", 12.0),
        ("1,5E-3", 0.0),
        (1234.5, 1234.5),
        (7, 7.0),
        (0.333333, 0.33),
    ],
)
def test_parse_ganho_aceita_texto_pt_br_e_numero(valor, esperado):
    # planilhas 2021-2024 gravam Ganho mes R$ como texto com virgula decimal
    assert parse_ganho(valor) == esperado


@pytest.mark.parametrize("valor", [None, float("nan"), "", "  "])
def test_parse_ganho_vazio_vira_nulo(valor):
    assert parse_ganho(valor) is None


def test_parse_ganho_texto_invalido_para_o_script():
    # virar nulo em silencio era o bug: o ganho sumia
    with pytest.raises(GanhosHistError, match="n/d"):
        parse_ganho("n/d")


def test_normalize_ignora_arquivo_mes_anterior():
    # o mes.anterior repete as linhas da FAP com a data deslocada; so serve de volume
    # do offset 2 (mel_volume_real_hist)
    out = normalize(_planilha(_linha(arquivo=ANTERIOR_2021), _linha()), {FAP})

    assert out.arquivo_origem.tolist() == [NORMAL_2021]


def test_normalize_mantem_todas_as_linhas_da_fap_no_grao_da_planilha():
    # varias linhas por FAP + codigo (operacoes/mix); o Qlik somava todas
    out = normalize(
        _planilha(_linha(campos={"MIX": 60.0}), _linha(campos={"MIX": 40.0}), _linha(cod="5320")),
        {FAP},
    )

    assert out.id.tolist() == [1, 2, 3]


def test_normalize_fap_em_dois_arquivos_normais_fica_com_o_mais_recente():
    # dez/2024 esta em 2024.app.1 e 2025.app.2; a FAP inteira vem de um arquivo so
    out = normalize(
        _planilha(
            _linha(arquivo=NORMAL_2024, campos={"MIX": 10.0}),
            _linha(arquivo=NORMAL_2024, campos={"MIX": 20.0}),
            _linha(arquivo=NORMAL_2025, campos={"MIX": 30.0}),
        ),
        {FAP},
    )

    assert out.arquivo_origem.tolist() == [NORMAL_2025]
    assert out.mix.tolist() == [30.0]


def test_normalize_atributos_da_fap_ficam_iguais_em_todas_as_linhas():
    # fct_ganhos agrupa por FAP + data/idealizador/setor: valor diferente entre linhas
    # da mesma FAP duplicaria a FAP no mes. Data: a menor; demais: o primeiro nao nulo.
    out = normalize(
        _planilha(
            _linha(cod="1", campos={"Data da FAP": dt.datetime(2021, 1, 5), "cracha": None}),
            _linha(cod="2", campos={"Data da FAP": dt.datetime(2021, 1, 4), "Setor": "Outro"}),
        ),
        {FAP},
    )

    assert out.dt_fap.tolist() == [dt.date(2021, 1, 4)] * 2
    assert out.cracha_idealizador.tolist() == [13783497] * 2
    assert out.setor.tolist() == ["Plastisol"] * 2


def test_normalize_id_sequencial_e_deterministico_pela_fap():
    linhas = [_linha(fap="B"), _linha(fap="A", cod="2"), _linha(fap="A", cod="1")]

    out = normalize(_planilha(*linhas), {"A", "B"})
    invertido = normalize(_planilha(*reversed(linhas)), {"A", "B"})

    assert out.numero_fap.tolist() == ["A", "A", "B"]
    assert out.id.tolist() == [1, 2, 3]
    assert out.cod_prod.tolist() == invertido.cod_prod.tolist()


def test_normalize_texto_numerico_do_excel_vira_string_sem_decimal():
    out = normalize(_planilha(_linha(fap=31032024032101.0, cod=2247255.0)), {"31032024032101"})

    assert (out.numero_fap[0], out.cod_prod[0]) == ("31032024032101", "2247255")


def test_normalize_fap_numerica_sem_zero_a_esquerda_casa_com_a_lista():
    # o Excel tirou o zero da celula numerica; a lista de FAPs vem do banco, com zero
    out = normalize(_planilha(_linha(fap=3032020122401.0)), {"03032020122401"})

    assert out.numero_fap.tolist() == ["03032020122401"]


@pytest.mark.parametrize("cod", [None, "  ", "000"])
def test_normalize_tipo_com_volume_sem_codigo_fica_com_sem_codigo(cod):
    # mesmo codigo que mel_volume_real_hist da ao volume da linha: o ganho casa no dbt
    out = normalize(_planilha(_linha(cod=cod), _linha(cod="1")), {FAP})

    assert out.cod_prod.tolist() == ["1", SEM_CODIGO]


def test_normalize_valores_invalidos_viram_nulo():
    out = normalize(
        _planilha(
            _linha(
                campos={"cracha": "n/d", "T.C. Anterior": "-", "Data da FAP": None, "Setor": " "}
            )
        ),
        {FAP},
    )

    row = out.iloc[0]
    assert row.cracha_idealizador is None
    assert pd.isna(row.tc_anterior)
    assert row.dt_fap is None
    assert row.setor is None


def test_normalize_cracha_numerico_do_excel_vira_inteiro():
    out = normalize(_planilha(_linha(campos={"cracha": 13783497.0})), {FAP})

    assert out.cracha_idealizador.tolist() == [13783497]


def test_normalize_falha_sem_coluna_obrigatoria():
    with pytest.raises(GanhosHistError, match="Setor Macro"):
        normalize(_planilha(_linha()).drop(columns="Setor Macro"), {FAP})


def test_read_faps_le_export_do_dbeaver(tmp_path):
    path = tmp_path / "faps.csv"
    path.write_text('﻿"numero_fap"\n"0203202105050"\n 23032021010404 \n\n', encoding="utf-8")

    assert read_faps(path) == {"0203202105050", "23032021010404"}


def test_read_faps_falha_sem_coluna_numero_fap(tmp_path):
    path = tmp_path / "faps.csv"
    path.write_text("fap\n1\n", encoding="utf-8")

    with pytest.raises(GanhosHistError, match="numero_fap"):
        read_faps(path)


def _normalizado(n, **extra):
    base = normalize(_planilha(_linha()), {FAP}).iloc[0].to_dict()
    return pd.DataFrame([{**base, "id": i + 1, **extra} for i in range(n)])


def test_render_sql_recarrega_a_tabela_numa_transacao():
    sql = render_sql(_normalizado(1))

    assert "create table dbo.mel_ganhos_hist" in sql
    assert "alter table dbo.mel_ganhos_hist add ganho_previsto decimal(18,2) null" in sql
    assert sql.index("alter column cod_prod") < sql.index("begin transaction")
    assert sql.index("begin transaction") < sql.index("delete from dbo.mel_ganhos_hist")
    assert sql.index("delete from") < sql.index("insert into") < sql.index("commit")
    assert (
        f"(1, N'{FAP}', N'224374', '2021-01-01', N'Tempo Ciclo', N'Sobral', N'Plastisol', "
        "N'Montagem', 10.0, 8.0, 46.0, 0.3, 0.25, 12.5, 1.2, 1.1, null, 13783497, N'Ana', "
        f"N'Beatriz', N'Analista de Processos', N'TC / MP', N'Não', N'{NORMAL_2021}')"
    ) in sql


def test_render_sql_nulos_viram_null():
    sql = render_sql(
        _normalizado(1, dt_fap=None, setor=None, tc_anterior=float("nan"), cracha_idealizador=None)
    )

    inicio = f"(1, N'{FAP}', N'224374', null, N'Tempo Ciclo', N'Sobral', null, N'Montagem', null,"
    assert inicio in sql
    assert ", null, null, N'Ana'," in sql


def test_render_sql_ganho_previsto_dos_demais_tipos():
    sql = render_sql(normalize(_planilha(_linha(tipo="FAO", cod=None)), {FAP}))

    assert f"(1, N'{FAP}', null, '2021-01-01', N'FAO'," in sql
    assert ", 40286.88, 13783497," in sql


def test_render_sql_aborta_se_fap_ja_existe_em_mel_ganhos_ou_nao_esta_aprovada():
    # disjuncao garantida no momento da carga: a lista de FAPs pode estar velha
    sql = render_sql(_normalizado(1))

    guards = sql[sql.index("insert into") : sql.index("commit")]
    assert "from dbo.mel_ganhos as g" in guards
    # FAP de mel_ganhos_fonte_planilha tem linha em mel_ganhos e nao aborta a carga
    assert "from dbo.mel_ganhos_fonte_planilha as p" in guards
    assert "a.status = 'Aprovado'" in guards
    assert "throw 50001" in guards
    assert "throw 50002" in guards


def test_render_sql_quebra_insert_em_lotes_de_1000_linhas():
    lotes_esperados = 3  # 1000 + 1000 + 1

    sql = render_sql(_normalizado(2001))

    assert sql.count("insert into dbo.mel_ganhos_hist") == lotes_esperados


def _seed(tmp_path, monkeypatch, *faps):
    seed = tmp_path / "mel_ganhos_fonte_planilha.csv"
    linhas = "".join(f"{fap},cadastro incompleto,detalhe\n" for fap in faps)
    seed.write_text(f"numero_fap,motivo,detalhe\n{linhas}", encoding="utf-8")
    monkeypatch.setattr("melhorias.scripts.ganhos_hist.FONTE_PLANILHA_SEED", seed)


def test_main_gera_o_sql_das_planilhas_filtradas_pela_lista(tmp_path, monkeypatch):
    planilhas = tmp_path / "planilhas"
    planilhas.mkdir()
    (planilhas / NORMAL_2021).touch()
    faps = tmp_path / "faps.csv"
    faps.write_text(f"numero_fap\n{FAP}\n", encoding="utf-8")
    out = tmp_path / "carga.sql"
    _seed(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "melhorias.scripts.ganhos_hist.read_spreadsheet",
        lambda path: _planilha(_linha(arquivo=path.name), _linha(arquivo=path.name, fap="X")),
    )

    assert main([str(planilhas), str(faps), str(out)]) == 0

    sql = out.read_text(encoding="utf-8")
    assert sql.count(f"N'{FAP}'") == 1
    assert "N'X'" not in sql


def test_main_leva_as_faps_do_seed_fonte_planilha(tmp_path, monkeypatch):
    # FAP com linha em mel_ganhos (fora da lista) cujo ganho vem da planilha
    planilhas = tmp_path / "planilhas"
    planilhas.mkdir()
    (planilhas / NORMAL_2021).touch()
    faps = tmp_path / "faps.csv"
    faps.write_text(f"numero_fap\n{FAP}\n", encoding="utf-8")
    out = tmp_path / "carga.sql"
    _seed(tmp_path, monkeypatch, "X")
    monkeypatch.setattr(
        "melhorias.scripts.ganhos_hist.read_spreadsheet",
        lambda path: _planilha(
            _linha(arquivo=path.name),
            _linha(arquivo=path.name, fap="X"),
            _linha(arquivo=path.name, fap="Y"),
        ),
    )

    assert main([str(planilhas), str(faps), str(out)]) == 0

    sql = out.read_text(encoding="utf-8")
    assert sql.count(f"N'{FAP}'") == 1
    assert sql.count("N'X'") == 1
    assert "N'Y'" not in sql


def test_seed_fonte_planilha_do_repo_tem_uma_linha_por_fap():
    seed = pd.read_csv(FONTE_PLANILHA_SEED, dtype=str)

    assert list(seed.columns) == ["numero_fap", "motivo", "detalhe"]
    assert seed.numero_fap.is_unique
    assert read_faps(FONTE_PLANILHA_SEED) == set(seed.numero_fap)
    assert set(seed.motivo) <= {"cadastro incompleto", "cadastro divergente"}


def test_main_falha_sem_planilhas(tmp_path):
    faps = tmp_path / "faps.csv"
    faps.write_text("numero_fap\n1\n", encoding="utf-8")

    with pytest.raises(GanhosHistError, match="nenhuma planilha"):
        main([str(tmp_path), str(faps), str(tmp_path / "out.sql")])
