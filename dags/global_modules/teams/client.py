"""Transporte HTTP das notificações do Teams.

Responsabilidades exclusivas deste módulo: resolver a URL do webhook, enviar o
payload com timeout, repetir falhas transitórias e traduzir a resposta em
sucesso ou exceção. A montagem do card fica em `cards.py` / `templates.py`.
"""

import json
import logging
import time
from http import HTTPStatus

import requests
from airflow.models import Variable
from global_modules.teams.redaction import redact_payload

logger = logging.getLogger(__name__)

# Nome da Airflow Variable lida quando nenhuma URL é passada explicitamente.
DEFAULT_WEBHOOK_VARIABLE = "WEBHOOK_TEAMS"

DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0

# O Incoming Webhook responde 200; o Power Automate Workflow responde 202.
SUCCESS_STATUSES = frozenset({HTTPStatus.OK, HTTPStatus.ACCEPTED})

HEADERS = {"Content-Type": "application/json"}


class TeamsNotificationError(RuntimeError):
    """Falha no envio da notificação após esgotar as tentativas."""


def _resolve_webhook_url(webhook_url: str | None, variable_name: str) -> str:
    """Resolve a URL do webhook.

    A Variable é lida aqui, e não no import do módulo, para não gerar uma query
    no metastore a cada parse de DAG.
    """
    resolved = webhook_url or Variable.get(variable_name, default_var=None)
    if not resolved:
        raise TeamsNotificationError(
            f"URL do webhook indisponível: Airflow Variable '{variable_name}' não definida."
        )
    return resolved


def _is_retryable(status_code: int) -> bool:
    """Só repete em 429 e em erros de servidor; 4xx restante é erro do payload."""
    is_rate_limited = status_code == HTTPStatus.TOO_MANY_REQUESTS
    is_server_error = status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    return is_rate_limited or is_server_error


def _post_once(url: str, payload: dict, timeout: float) -> requests.Response:
    return requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=timeout)


def _sleep_backoff(attempt: int) -> None:
    time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))


def send_payload(
    payload: dict,
    webhook_url: str | None = None,
    variable_name: str = DEFAULT_WEBHOOK_VARIABLE,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> None:
    """Envia um payload já montado para o webhook, com timeout e backoff exponencial.

    Toda string do payload passa por `redact_payload` antes do envio: é a última
    barreira contra credenciais em cards e textos, inclusive os montados à mão.

    :param payload: Corpo JSON da mensagem.
    :param webhook_url: URL do webhook; se ausente, lê da Airflow Variable.
    :param variable_name: Nome da Variable usada quando `webhook_url` é omitido.
    :param timeout: Timeout de cada requisição, em segundos.
    :param retries: Número de tentativas totais (não apenas as repetições).
    :raises TeamsNotificationError: Quando todas as tentativas falham.
    """
    url = _resolve_webhook_url(webhook_url, variable_name)
    safe_payload = redact_payload(payload)
    last_error = ""

    for attempt in range(retries):
        try:
            response = _post_once(url, safe_payload, timeout)
        except requests.RequestException as exc:
            last_error = f"erro de conexão: {exc}"
        else:
            if response.status_code in SUCCESS_STATUSES:
                logger.info("Notificação enviada ao Teams (HTTP %s).", response.status_code)
                return

            last_error = f"HTTP {response.status_code}: {response.text}"
            if not _is_retryable(response.status_code):
                raise TeamsNotificationError(f"Falha ao enviar notificação: {last_error}")

        is_last_attempt = attempt == retries - 1
        if is_last_attempt:
            break

        logger.warning(
            "Tentativa %s/%s de envio ao Teams falhou (%s). Repetindo.",
            attempt + 1,
            retries,
            last_error,
        )
        _sleep_backoff(attempt)

    raise TeamsNotificationError(
        f"Falha ao enviar notificação após {retries} tentativas: {last_error}"
    )


def send_card(
    card: dict,
    webhook_url: str | None = None,
    variable_name: str = DEFAULT_WEBHOOK_VARIABLE,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> None:
    """Envia um Adaptive Card montado por `cards.build_card` ou por um template."""
    send_payload(card, webhook_url, variable_name, timeout, retries)


def send_text(
    message: str,
    webhook_url: str | None = None,
    variable_name: str = DEFAULT_WEBHOOK_VARIABLE,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> None:
    """Envia uma mensagem de texto puro.

    Mantido para compatibilidade com os chamadores anteriores aos cards.
    """
    send_payload({"text": message}, webhook_url, variable_name, timeout, retries)
