"""Callbacks do Airflow que notificam o Teams."""

from global_modules.teams.client import send_card
from global_modules.teams.templates import dag_failure_card


def notify_teams_on_failure(context) -> None:
    """Callback de falha de task: envia o Adaptive Card com link para os logs.

    :param context: Contexto fornecido pelo Airflow ao `on_failure_callback`.
    """
    send_card(dag_failure_card(context))
