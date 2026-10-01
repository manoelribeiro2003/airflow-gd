"""Testes dos cards prontos."""

from types import SimpleNamespace

import pytest
from global_modules.teams.cards import COLOR_ACCENT, COLOR_ATTENTION, COLOR_GOOD
from global_modules.teams.templates import (
    MAX_EXCEPTION_LENGTH,
    alert_card,
    dag_failure_card,
    info_card,
)

LOG_URL = "https://airflow.local/log?dag_id=X"

# Card informativo sem mensagem: cabecalho + FactSet.
BLOCOS_SEM_MENSAGEM = 2


def _contexto(**overrides):
    contexto = {
        "dag": SimpleNamespace(dag_id="BRONZE_F_AREA"),
        "dag_run": SimpleNamespace(run_id="manual__2026-08-21"),
        "task_instance": SimpleNamespace(task_id="extrai", try_number=2, log_url=LOG_URL),
    }
    return {**contexto, **overrides}


def _conteudo(card):
    return card["attachments"][0]["content"]


def _facts(card):
    fact_set = next(item for item in _conteudo(card)["body"] if item["type"] == "FactSet")
    return {fact["title"]: fact["value"] for fact in fact_set["facts"]}


def test_card_de_falha_traz_dag_task_run_e_tentativa():
    facts = _facts(dag_failure_card(_contexto()))

    assert facts["DAG"] == "BRONZE_F_AREA"
    assert facts["Task"] == "extrai"
    assert facts["Run"] == "manual__2026-08-21"
    assert facts["Tentativa"] == "2"


def test_card_de_falha_usa_cor_de_atencao_e_cita_a_dag_no_titulo():
    conteudo = _conteudo(dag_failure_card(_contexto()))
    cabecalho = conteudo["body"][0]

    assert cabecalho["color"] == COLOR_ATTENTION
    assert "BRONZE_F_AREA" in cabecalho["text"]


def test_card_de_falha_tem_botao_para_os_logs():
    acoes = _conteudo(dag_failure_card(_contexto()))["actions"]

    assert acoes[0]["url"] == LOG_URL


def test_card_de_falha_sem_log_url_nao_cria_botao():
    contexto = _contexto(task_instance=SimpleNamespace(task_id="extrai", try_number=1))

    assert "actions" not in _conteudo(dag_failure_card(contexto))


def test_card_de_falha_inclui_a_excecao_quando_presente():
    facts = _facts(dag_failure_card(_contexto(exception=ValueError("conexao recusada"))))

    assert facts["Erro"] == "conexao recusada"


def test_excecao_muito_longa_e_truncada():
    facts = _facts(dag_failure_card(_contexto(exception=ValueError("x" * 5000))))

    assert len(facts["Erro"]) <= MAX_EXCEPTION_LENGTH


def test_card_de_falha_tolera_contexto_incompleto():
    facts = _facts(dag_failure_card({}))

    assert facts["DAG"] == "desconhecida"


@pytest.mark.parametrize(
    ("severity", "color"),
    [("error", COLOR_ATTENTION), ("success", COLOR_GOOD), ("desconhecida", COLOR_ACCENT)],
)
def test_alert_card_mapeia_severidade_para_cor(severity, color):
    card = alert_card("Titulo", {"Setor": "Injecao"}, severity=severity)

    assert _conteudo(card)["body"][0]["color"] == color


def test_info_card_coloca_a_mensagem_antes_dos_campos():
    corpo = _conteudo(info_card("Titulo", {"Setor": "Injecao"}, message="detalhe"))["body"]

    assert corpo[1]["text"] == "detalhe"
    assert corpo[2]["type"] == "FactSet"


def test_info_card_sem_mensagem_so_tem_cabecalho_e_campos():
    corpo = _conteudo(info_card("Titulo", {"Setor": "Injecao"}))["body"]

    assert len(corpo) == BLOCOS_SEM_MENSAGEM


def test_card_de_falha_nao_vaza_senha_da_string_de_conexao():
    erro = RuntimeError(
        'Unable to connect to Postgres at "postgresql://reader:s3nh4@10.1.4.10:5000/db"'
    )

    facts = _facts(dag_failure_card(_contexto(exception=erro)))

    assert "s3nh4" not in facts["Erro"]
    assert "10.1.4.10" in facts["Erro"]
