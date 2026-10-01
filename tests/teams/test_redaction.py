"""Testes da remoção de credenciais das mensagens enviadas ao Teams."""

import pytest
from global_modules.teams.redaction import MASK, redact_payload, redact_secrets

SENHA = "cJKugZMqTsv0"


@pytest.mark.parametrize(
    "texto",
    [
        f'Unable to connect to Postgres at "postgresql://reader:{SENHA}@10.1.4.10:5000/workflow"',
        f"mssql+pyodbc://sa:{SENHA}@servidor/db?driver=ODBC",
        f"postgresql://reader:{SENHA}@x@10.1.4.10/db",
        f"host=10.1.4.10 port=5000 user=reader password={SENHA} dbname=workflow",
        f"host=10.1.4.10 password='{SENHA} com espaco' dbname=workflow",
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=srv;UID=sa;PWD={SENHA};",
        f"UID=sa;PWD={{{SENHA};x}};DATABASE=db",
        f"https://api/x?token={SENHA}&page=1",
    ],
)
def test_remove_a_senha(texto):
    resultado = redact_secrets(texto)

    assert SENHA not in resultado
    assert MASK in resultado


def test_preserva_usuario_e_host_da_uri():
    resultado = redact_secrets(f"postgresql://reader:{SENHA}@10.1.4.10:5000/workflow")

    assert resultado == f"postgresql://reader:{MASK}@10.1.4.10:5000/workflow"


def test_preserva_campos_nao_sensiveis_do_odbc():
    resultado = redact_secrets(f"SERVER=srv;UID=sa;PWD={SENHA};DATABASE=db")

    assert resultado == f"SERVER=srv;UID=sa;PWD={MASK};DATABASE=db"


def test_texto_sem_credenciais_nao_muda():
    texto = 'connection to server at "10.1.4.10", port 5000 failed: No route to host'

    assert redact_secrets(texto) == texto


def test_mascara_assinatura_do_webhook():
    url = f"https://prod.logic.azure.com/workflows/x/invoke?api-version=1&sig={SENHA}"

    assert SENHA not in redact_secrets(url)


def test_redact_payload_percorre_listas_e_dicts_sem_mutar():
    payload = {"body": [{"text": f"PWD={SENHA};"}, 1, None]}

    resultado = redact_payload(payload)

    assert SENHA not in str(resultado)
    assert resultado["body"][1:] == [1, None]
    assert payload["body"][0]["text"] == f"PWD={SENHA};"
