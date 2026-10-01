"""Remove credenciais de textos livres antes de enviá-los ao Teams."""

import re

from airflow.utils.log.secrets_masker import redact

MASK = "***"

# Userinfo de URIs (postgresql://user:senha@host). Guloso até o último `@` do token
# para cobrir senhas que contêm `@`.
_URI_PASSWORD = re.compile(
    r"(?P<prefix>[a-z][a-z0-9+.-]*://[^:/\s@'\"]*:)[^\s'\"]*@", re.IGNORECASE
)

# Pares chave=valor de libpq, ODBC e query strings (password=..., PWD={...};).
# `sig` é a assinatura da URL do webhook do Power Automate, que aparece em erros do requests.
_SECRET_KEYS = r"password|passwd|pwd|secret|client_secret|token|access_token|api_key|apikey|sig"
_KEY_VALUE_SECRET = re.compile(
    rf"(?P<prefix>\b(?:{_SECRET_KEYS})\s*=\s*)"
    r"(?:'[^']*'|\"[^\"]*\"|\{[^}]*\}|[^\s;&,'\"]+)",
    re.IGNORECASE,
)


def redact_secrets(text: str) -> str:
    """Mascara senhas embutidas em URIs e pares chave=valor.

    Aplica também o masker do Airflow, que cobre segredos já registrados
    (senhas de Connections, Variables sensíveis).
    """
    masked = str(redact(text))
    masked = _URI_PASSWORD.sub(rf"\g<prefix>{MASK}@", masked)
    return _KEY_VALUE_SECRET.sub(rf"\g<prefix>{MASK}", masked)


def redact_payload(value):
    """Aplica `redact_secrets` em todas as strings de um payload, sem mutar a entrada."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {key: redact_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_payload(item) for item in value]
    return value
