"""Cards prontos para os casos de uso recorrentes das DAGs."""

from datetime import datetime
from zoneinfo import ZoneInfo

from global_modules.teams.cards import (
    COLOR_ACCENT,
    COLOR_ATTENTION,
    SEVERITY_COLORS,
    build_card,
    fact_set,
    open_url_action,
    text_block,
)
from global_modules.teams.redaction import redact_secrets

TIMEZONE = ZoneInfo("America/Fortaleza")
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

# Traceback completo estoura o limite de payload do Teams; o início já identifica a causa.
MAX_EXCEPTION_LENGTH = 1500


def _now() -> str:
    return datetime.now(TIMEZONE).strftime(DATETIME_FORMAT)


def _failure_facts(context: dict) -> dict:
    """Extrai os campos da falha do contexto do Airflow, tolerando chaves ausentes."""
    dag = context.get("dag")
    dag_run = context.get("dag_run")
    task_instance = context.get("task_instance")

    facts = {
        "DAG": getattr(dag, "dag_id", "desconhecida"),
        "Task": getattr(task_instance, "task_id", "desconhecida"),
        "Run": getattr(dag_run, "run_id", "desconhecida"),
        "Tentativa": getattr(task_instance, "try_number", "-"),
        "Data": _now(),
    }

    exception = context.get("exception")
    if exception:
        # Mensagens de driver costumam ecoar a string de conexão com a senha.
        facts["Erro"] = redact_secrets(str(exception))[:MAX_EXCEPTION_LENGTH]

    return facts


def dag_failure_card(context: dict) -> dict:
    """Monta o card de falha de task a partir do contexto do `on_failure_callback`."""
    dag_id = getattr(context.get("dag"), "dag_id", "desconhecida")
    log_url = getattr(context.get("task_instance"), "log_url", None)

    actions = [open_url_action("Abrir logs no Airflow", log_url)] if log_url else None

    return build_card(
        title=f"Falha na DAG {dag_id}",
        body=[fact_set(_failure_facts(context))],
        color=COLOR_ATTENTION,
        actions=actions,
    )


def alert_card(title: str, facts: dict, severity: str = "warning") -> dict:
    """Monta um card de alerta genérico.

    :param severity: `info`, `success`, `warning` ou `error`.
    """
    return build_card(
        title=title,
        body=[fact_set(facts)],
        color=SEVERITY_COLORS.get(severity, COLOR_ACCENT),
    )


def info_card(title: str, facts: dict, message: str = "") -> dict:
    """Monta um card informativo, com um texto opcional acima dos campos."""
    body = [text_block(message)] if message else []
    body.append(fact_set(facts))

    return build_card(title=title, body=body, color=COLOR_ACCENT)
