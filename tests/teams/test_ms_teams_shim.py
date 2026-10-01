"""Garante que os imports legados de `global_modules.ms_teams` continuam válidos."""

from types import SimpleNamespace

from global_modules import ms_teams
from global_modules.teams import callbacks


def test_notify_teams_on_failure_envia_o_card_de_falha(monkeypatch):
    enviados = []
    monkeypatch.setattr(callbacks, "send_card", enviados.append)

    contexto = {
        "dag": SimpleNamespace(dag_id="BRONZE_F_AREA"),
        "dag_run": SimpleNamespace(run_id="run-1"),
        "task_instance": SimpleNamespace(task_id="extrai", try_number=1, log_url="https://x"),
    }
    ms_teams.notify_teams_on_failure(contexto)

    assert enviados[0]["attachments"][0]["content"]["type"] == "AdaptiveCard"


def test_send_teams_message_envia_texto(monkeypatch):
    enviados = []
    monkeypatch.setattr(ms_teams, "send_text", enviados.append)

    ms_teams.send_teams_message("mensagem")

    assert enviados == ["mensagem"]
