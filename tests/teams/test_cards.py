"""Testes das primitivas de composição do Adaptive Card."""

from global_modules.teams.cards import (
    CARD_CONTENT_TYPE,
    CARD_VERSION,
    COLOR_ATTENTION,
    MAX_TEXT_LENGTH,
    build_card,
    fact_set,
    open_url_action,
    text_block,
    truncate,
    two_columns,
)


def test_text_block_tem_wrap_por_padrao():
    assert text_block("oi") == {"type": "TextBlock", "text": "oi", "wrap": True}


def test_kwargs_snake_case_viram_camel_case():
    block = text_block("oi", horizontal_alignment="Center", weight="Bolder")
    assert block["horizontalAlignment"] == "Center"
    assert block["weight"] == "Bolder"


def test_kwargs_none_sao_descartados():
    assert "color" not in text_block("oi", color=None)


def test_truncate_preserva_o_inicio():
    assert truncate("abcdef", limit=5) == "ab..."


def test_texto_longo_e_truncado_no_bloco():
    block = text_block("x" * (MAX_TEXT_LENGTH + 100))
    assert len(block["text"]) == MAX_TEXT_LENGTH


def test_fact_set_converte_mapa_em_facts():
    assert fact_set({"Setor": "Injecao", "Maquina": 12}) == {
        "type": "FactSet",
        "facts": [
            {"title": "Setor", "value": "Injecao"},
            {"title": "Maquina", "value": "12"},
        ],
    }


def test_two_columns_distribui_os_blocos():
    columns = two_columns(text_block("a"), text_block("b"))["columns"]
    assert [col["items"][0]["text"] for col in columns] == ["a", "b"]


def test_open_url_action():
    assert open_url_action("Abrir", "https://x") == {
        "type": "Action.OpenUrl",
        "title": "Abrir",
        "url": "https://x",
    }


def test_build_card_monta_o_envelope_da_mensagem():
    card = build_card("Titulo", body=[text_block("corpo")])

    assert card["type"] == "message"
    attachment = card["attachments"][0]
    assert attachment["contentType"] == CARD_CONTENT_TYPE
    assert attachment["content"]["version"] == CARD_VERSION


def test_build_card_usa_o_titulo_como_cabecalho_colorido():
    header = build_card("Falhou", body=[], color=COLOR_ATTENTION)["attachments"][0]["content"][
        "body"
    ][0]

    assert header["text"] == "Falhou"
    assert header["color"] == COLOR_ATTENTION
    assert header["size"] == "Large"


def test_build_card_sem_actions_nao_cria_a_chave():
    assert "actions" not in build_card("t", body=[])["attachments"][0]["content"]


def test_build_card_inclui_actions_quando_informadas():
    action = open_url_action("Abrir", "https://x")
    content = build_card("t", body=[], actions=[action])["attachments"][0]["content"]

    assert content["actions"] == [action]


def test_build_card_nao_muta_o_corpo_recebido():
    body = [text_block("corpo")]
    build_card("t", body=body)

    assert len(body) == 1


def test_text_block_mascara_senha():
    assert "s3nh4" not in text_block("postgresql://reader:s3nh4@host/db")["text"]


def test_fact_set_mascara_senha():
    facts = fact_set({"Conexao": "host=x password=s3nh4"})["facts"]

    assert "s3nh4" not in facts[0]["value"]


def test_senha_no_ponto_de_corte_e_mascarada_antes_de_truncar():
    prefixo = "x" * (MAX_TEXT_LENGTH - 30)
    block = text_block(f"{prefixo} postgresql://reader:s3nh4segredo@host/db")

    assert "s3nh4" not in block["text"]
