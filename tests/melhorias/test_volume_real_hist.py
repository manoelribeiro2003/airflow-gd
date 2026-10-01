"""Testes da geracao da carga de mel_volume_real_hist a partir das planilhas do Qlik."""

import pandas as pd
import pytest
import xlsxwriter
from melhorias.scripts.volume_real_hist import (
    SEM_CODIGO,
    VolumeHistError,
    fap_key,
    normalize,
    parse_filename,
    read_spreadsheet,
    render_sql,
)

NORMAL_2024 = "BASE_LANC_MELHORIAS_2024_Sobral.app.1.xlsx"
NORMAL_2025 = "BASE_LANC_MELHORIAS_2025_Sobral.app.2.xlsx"
ANTERIOR_2025 = "BASE_LANC_MELHORIAS_2025_Sobral.app.mês.anterior.xlsx"


def _linha(
    arquivo: str = NORMAL_2025,
    fap: object = "25082025052701",
    cod: object = "83845",
    volume: object = 8160.0,
    tipo: object = "Tempo Ciclo",
) -> dict[str, object]:
    return {
        "arquivo": arquivo,
        "Tipo de Melhoria": tipo,
        "Nº F.A.P": fap,
        "Código": cod,
        "1º Mês": volume,
    }


def _planilha(*linhas):
    return pd.DataFrame(list(linhas))


def _chaves(out):
    return list(zip(out.numero_fap, out.cod_prod, out.mes_offset, out.volume))


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("BASE_LANC_MELHORIAS_2021_Sobral.app.1.xlsx", (2021, 1)),
        ("BASE_LANC_MELHORIAS_2022_Sobral.app.2.xlsx", (2022, 1)),
        ("BASE_LANC_MELHORIAS_2023_Sobral.app.mês.anterior.xlsx", (2023, 2)),
    ],
)
def test_parse_filename_offset_vem_do_nome_do_arquivo(nome, esperado):
    assert parse_filename(nome) == esperado


def test_parse_filename_aceita_mes_decomposto_do_windows():
    nome = "BASE_LANC_MELHORIAS_2024_Sobral.app.mês.anterior.xlsx"

    assert parse_filename(nome) == (2024, 2)


def test_parse_filename_falha_fora_do_padrao():
    with pytest.raises(VolumeHistError, match="carga_horaria.xlsx"):
        parse_filename("carga_horaria.xlsx")


def test_normalize_arquivo_normal_vira_offset_1():
    out = normalize(_planilha(_linha()))

    assert list(out.columns) == ["numero_fap", "cod_prod", "mes_offset", "volume", "arquivo_origem"]
    assert out.iloc[0].to_dict() == {
        "numero_fap": "25082025052701",
        "cod_prod": "83845",
        "mes_offset": 1,
        "volume": 8160.0,
        "arquivo_origem": NORMAL_2025,
    }


def test_normalize_mes_anterior_vira_offset_2_independente_da_data():
    # "Data da FAP" do mes.anterior e dt_fap+30 (ou +60 por erro); o offset sai do
    # nome do arquivo, entao a data nem entra no calculo.
    out = normalize(
        _planilha(
            {**_linha(arquivo=ANTERIOR_2025, fap="A"), "Data da FAP": "2025-03-03"},
            {**_linha(arquivo=ANTERIOR_2025, fap="B"), "Data da FAP": "2025-04-02"},
        )
    )

    assert list(out.mes_offset) == [2, 2]


def test_normalize_dezembro_no_mes_anterior_do_ano_seguinte_fica_na_fap_de_dezembro():
    out = normalize(
        _planilha(
            _linha(arquivo=NORMAL_2024, fap="10032024120501", volume=100.0),
            _linha(arquivo=ANTERIOR_2025, fap="10032024120501", volume=200.0),
        )
    )

    assert _chaves(out) == [
        ("10032024120501", "83845", 1, 100.0),
        ("10032024120501", "83845", 2, 200.0),
    ]


def test_normalize_chave_em_dois_arquivos_prevalece_o_mais_recente():
    out = normalize(
        _planilha(
            _linha(arquivo=NORMAL_2025, volume=900.0),
            _linha(arquivo=NORMAL_2024, volume=100.0),
        )
    )

    assert _chaves(out) == [("25082025052701", "83845", 1, 900.0)]
    assert out.arquivo_origem.tolist() == [NORMAL_2025]


def test_normalize_linhas_repetidas_da_mesma_chave_viram_uma():
    # uma linha por operacao/mix, todas com o mesmo volume
    out = normalize(_planilha(_linha(), _linha(), _linha()))

    assert len(out) == 1


def test_normalize_mesma_chave_com_volumes_diferentes_no_arquivo_fica_com_o_maior():
    # linha de mix 0 da FAP vem com volume 0 ao lado da linha com o volume real
    out = normalize(_planilha(_linha(volume=0.0), _linha(volume=15271.0)))

    assert _chaves(out) == [("25082025052701", "83845", 1, 15271.0)]


def test_normalize_texto_numerico_do_excel_vira_string_sem_decimal():
    out = normalize(_planilha(_linha(fap=31032024032101.0, cod=2247255.0)))

    assert (out.numero_fap[0], out.cod_prod[0]) == ("31032024032101", "2247255")


@pytest.mark.parametrize(
    ("celula", "esperado"),
    [
        # o Excel guardou a FAP como numero e tirou o zero: volta para 14 digitos
        (2032024111401.0, "02032024111401"),
        (5032024103101, "05032024103101"),
        # numero que ja tem 14 ou 15 digitos nao muda
        (31032024032101.0, "31032024032101"),
        (149102023081403.0, "149102023081403"),
        # FAP antiga de Crato: com o zero nao vira data valida, fica como veio
        (1908210204010.0, "1908210204010"),
        (190821020401.0, "190821020401"),
        # celula de texto nunca ganha zero: existe FAP de 13 digitos no SharePoint
        ("1172021042704", "1172021042704"),
        ("02032024111401", "02032024111401"),
        (None, None),
    ],
)
def test_fap_key_repoe_zero_a_esquerda_so_de_celula_numerica(celula, esperado):
    assert fap_key(celula) == esperado


def test_normalize_fap_sem_zero_cai_na_mesma_chave_da_fap_com_zero():
    # a mesma FAP aparece como texto numa linha e como numero (sem o zero) em outra
    out = normalize(
        _planilha(
            _linha(fap="02032024111401", cod="1", volume=10.0),
            _linha(fap=2032024111401.0, cod="2", volume=26020.0),
        )
    )

    assert _chaves(out) == [
        ("02032024111401", "1", 1, 10.0),
        ("02032024111401", "2", 1, 26020.0),
    ]


def test_normalize_codigo_sem_zeros_a_esquerda():
    # o Excel guarda o codigo como numero (0224374 -> 224374); a chave canonica e sem
    # zeros a esquerda e o dbt compara com mel_ganhos.cod_prod do mesmo jeito
    out = normalize(_planilha(_linha(fap="A", cod="0224374"), _linha(fap="B", cod=224374.0)))

    assert out.cod_prod.tolist() == ["224374", "224374"]


def test_normalize_codigo_com_e_sem_zero_na_mesma_fap_vira_uma_chave():
    out = normalize(_planilha(_linha(cod="05320", volume=0.0), _linha(cod=5320, volume=10.0)))

    assert _chaves(out) == [("25082025052701", "5320", 1, 10.0)]


def test_normalize_remove_espacos_das_chaves():
    out = normalize(_planilha(_linha(fap=" 25082025052701 ", cod=" 83845")))

    assert (out.numero_fap[0], out.cod_prod[0]) == ("25082025052701", "83845")


@pytest.mark.parametrize(
    "linha",
    [
        _linha(fap=None),
        # tipo sem ganho por volume: a linha nao tem codigo e o volume nao e usado
        _linha(cod=None, tipo="FAO"),
        _linha(cod="  ", tipo="FAO"),
        _linha(cod=None, tipo=None),
        _linha(volume=None),
        _linha(volume="n/d"),
    ],
)
def test_normalize_descarta_linha_sem_chave_ou_volume(linha):
    assert normalize(_planilha(linha, _linha(fap="OUTRA"))).numero_fap.tolist() == ["OUTRA"]


@pytest.mark.parametrize(
    "tipo", ["Tempo Ciclo", "Aglutinação", "Consumo", "Troca de Matéria Prima"]
)
@pytest.mark.parametrize("cod", [None, "  ", "000"])
def test_normalize_linha_sem_codigo_de_tipo_com_volume_fica_com_sem_codigo(tipo, cod):
    # o Qlik calculava o ganho na propria linha; mel_ganhos_hist grava o mesmo codigo
    out = normalize(_planilha(_linha(cod=cod, tipo=tipo, volume=1933092.0)))

    assert _chaves(out) == [("25082025052701", SEM_CODIGO, 1, 1933092.0)]


def test_normalize_mantem_volume_zero_e_negativo():
    out = normalize(_planilha(_linha(fap="A", volume=0.0), _linha(fap="B", volume=-837.0)))

    assert out.volume.tolist() == [0.0, -837.0]


def test_normalize_ordena_pela_chave():
    out = normalize(
        _planilha(
            _linha(arquivo=ANTERIOR_2025, fap="B"),
            _linha(fap="B"),
            _linha(fap="A", cod="2"),
            _linha(fap="A", cod="1"),
        )
    )

    assert [(r.numero_fap, r.cod_prod, r.mes_offset) for r in out.itertuples()] == [
        ("A", "1", 1),
        ("A", "2", 1),
        ("B", "83845", 1),
        ("B", "83845", 2),
    ]


@pytest.mark.parametrize("coluna", ["1º Mês", "Tipo de Melhoria"])
def test_normalize_falha_sem_coluna_obrigatoria(coluna):
    with pytest.raises(VolumeHistError, match=coluna):
        normalize(_planilha(_linha()).drop(columns=coluna))


def _xlsx(path, header, *rows):
    with xlsxwriter.Workbook(path) as wb:
        wb.add_worksheet("outra")
        ws = wb.add_worksheet("BASE_LANCAMENTO")
        for r, values in enumerate([header, *rows]):
            ws.write_row(r, 0, values)


def test_read_spreadsheet_le_colunas_ate_cracha_e_anota_o_arquivo(tmp_path):
    path = tmp_path / NORMAL_2025
    _xlsx(
        path,
        ["Tipo", "Nº F.A.P ", "Código", "1º Mês", "cracha", "Código"],
        ["TC", "25082025052701", 83845, 8160, "123", 999],
    )

    out = read_spreadsheet(path)

    assert out[["arquivo", "Nº F.A.P", "Código", "1º Mês"]].to_dict("records") == [
        {"arquivo": NORMAL_2025, "Nº F.A.P": "25082025052701", "Código": 83845, "1º Mês": 8160}
    ]


def test_read_spreadsheet_ignora_coluna_auxiliar_sem_nome(tmp_path):
    path = tmp_path / NORMAL_2025
    _xlsx(
        path,
        ["Tipo", "Nº F.A.P", "Código", None, "1º Mês", "cracha"],
        ["TC", "A", 1, "aux", 10, "123"],
    )

    out = read_spreadsheet(path)

    assert out["1º Mês"].tolist() == [10]
    assert not [c for c in out.columns if c.startswith("Unnamed")]


def _normalizado(n):
    return pd.DataFrame({
        "numero_fap": [f"FAP{i}" for i in range(n)],
        "cod_prod": ["83845"] * n,
        "mes_offset": [2] * n,
        "volume": [8160.0] * n,
        "arquivo_origem": [ANTERIOR_2025] * n,
    })


def test_render_sql_recarrega_a_tabela_numa_transacao():
    sql = render_sql(_normalizado(1))

    assert "create table dbo.mel_volume_real_hist" in sql
    assert "check (mes_offset in (1, 2))" in sql
    assert sql.index("begin transaction") < sql.index("delete from dbo.mel_volume_real_hist")
    assert sql.index("delete from") < sql.index("insert into") < sql.index("commit")
    assert f"(N'FAP0', N'83845', 2, 8160.0, N'{ANTERIOR_2025}')" in sql


def test_render_sql_quebra_insert_em_lotes_de_1000_linhas():
    lotes_esperados = 3  # 1000 + 1000 + 1

    sql = render_sql(_normalizado(2001))

    assert sql.count("insert into dbo.mel_volume_real_hist") == lotes_esperados
