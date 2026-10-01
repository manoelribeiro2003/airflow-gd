"""Testes do transporte HTTP das notificações do Teams."""

import json
from http import HTTPStatus

import pytest
import requests
from global_modules.teams import client
from global_modules.teams.client import TeamsNotificationError, send_card, send_payload, send_text

WEBHOOK = "https://webhook.invalido/teste"
TIMEOUT_SEGUNDOS = 2.5
UMA_TENTATIVA = 1
DUAS_TENTATIVAS = 2
TRES_TENTATIVAS = 3


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class FakePost:
    """Substitui `requests.post` devolvendo respostas pré-programadas em sequência."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers=None, data=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "data": data, "timeout": timeout})
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    """Remove o backoff real para os testes não dormirem."""
    monkeypatch.setattr(client.time, "sleep", lambda _: None)


def _instalar_post(monkeypatch, *responses):
    fake = FakePost(*responses)
    monkeypatch.setattr(client.requests, "post", fake)
    return fake


@pytest.mark.parametrize("status", [HTTPStatus.OK, HTTPStatus.ACCEPTED])
def test_200_e_202_sao_sucesso(monkeypatch, status):
    fake = _instalar_post(monkeypatch, FakeResponse(status))

    send_payload({"text": "oi"}, webhook_url=WEBHOOK)

    assert len(fake.calls) == UMA_TENTATIVA


def test_payload_enviado_como_json_com_timeout(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.OK))

    send_card({"type": "message"}, webhook_url=WEBHOOK, timeout=TIMEOUT_SEGUNDOS)

    call = fake.calls[0]
    assert call["url"] == WEBHOOK
    assert json.loads(call["data"]) == {"type": "message"}
    assert call["timeout"] == TIMEOUT_SEGUNDOS


def test_send_text_envia_texto_puro(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.OK))

    send_text("mensagem", webhook_url=WEBHOOK)

    assert json.loads(fake.calls[0]["data"]) == {"text": "mensagem"}


def test_erro_de_servidor_e_repetido_ate_o_sucesso(monkeypatch):
    fake = _instalar_post(
        monkeypatch,
        FakeResponse(HTTPStatus.INTERNAL_SERVER_ERROR, "boom"),
        FakeResponse(HTTPStatus.OK),
    )

    send_payload({"text": "oi"}, webhook_url=WEBHOOK)

    assert len(fake.calls) == DUAS_TENTATIVAS


def test_rate_limit_e_repetido(monkeypatch):
    fake = _instalar_post(
        monkeypatch,
        FakeResponse(HTTPStatus.TOO_MANY_REQUESTS),
        FakeResponse(HTTPStatus.ACCEPTED),
    )

    send_payload({"text": "oi"}, webhook_url=WEBHOOK)

    assert len(fake.calls) == DUAS_TENTATIVAS


def test_erro_de_conexao_e_repetido(monkeypatch):
    fake = _instalar_post(
        monkeypatch,
        requests.ConnectionError("sem rota"),
        FakeResponse(HTTPStatus.OK),
    )

    send_payload({"text": "oi"}, webhook_url=WEBHOOK)

    assert len(fake.calls) == DUAS_TENTATIVAS


def test_erro_de_cliente_nao_e_repetido(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.BAD_REQUEST, "payload invalido"))

    with pytest.raises(TeamsNotificationError, match="400"):
        send_payload({"text": "oi"}, webhook_url=WEBHOOK)

    assert len(fake.calls) == UMA_TENTATIVA


def test_falha_apos_esgotar_as_tentativas(monkeypatch):
    fake = _instalar_post(
        monkeypatch,
        *[FakeResponse(HTTPStatus.SERVICE_UNAVAILABLE, "indisponivel")] * TRES_TENTATIVAS,
    )

    with pytest.raises(TeamsNotificationError, match="3 tentativas"):
        send_payload({"text": "oi"}, webhook_url=WEBHOOK, retries=TRES_TENTATIVAS)

    assert len(fake.calls) == TRES_TENTATIVAS


def test_url_vem_da_variable_quando_omitida(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.OK))
    lidas = []

    class FakeVariable:
        @staticmethod
        def get(key, default_var=None):
            lidas.append(key)
            return WEBHOOK

    monkeypatch.setattr(client, "Variable", FakeVariable)
    send_payload({"text": "oi"})

    assert lidas == ["WEBHOOK_TEAMS"]
    assert fake.calls[0]["url"] == WEBHOOK


def test_variable_ausente_levanta_erro(monkeypatch):
    class FakeVariable:
        @staticmethod
        def get(key, default_var=None):
            return default_var

    monkeypatch.setattr(client, "Variable", FakeVariable)

    with pytest.raises(TeamsNotificationError, match="WEBHOOK_TEAMS"):
        send_payload({"text": "oi"})


def test_texto_puro_nao_vaza_senha(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.OK))

    send_text("falhou em postgresql://reader:s3nh4@10.1.4.10/db", webhook_url=WEBHOOK)

    assert "s3nh4" not in fake.calls[0]["data"]


def test_payload_montado_a_mao_nao_vaza_senha_nem_muta_a_entrada(monkeypatch):
    fake = _instalar_post(monkeypatch, FakeResponse(HTTPStatus.OK))
    payload = {"attachments": [{"content": {"body": [{"text": "PWD=s3nh4;"}]}}]}

    send_payload(payload, webhook_url=WEBHOOK)

    assert "s3nh4" not in fake.calls[0]["data"]
    assert payload["attachments"][0]["content"]["body"][0]["text"] == "PWD=s3nh4;"
