"""Notificações do Microsoft Teams via Adaptive Cards.

Uso típico dentro de uma DAG::

    from global_modules.teams import alert_card, send_card

    send_card(alert_card("Estoque abaixo do mínimo", {"SKU": "1234", "Saldo": "12"}))
"""

from global_modules.teams.callbacks import notify_teams_on_failure
from global_modules.teams.cards import (
    build_card,
    fact_set,
    open_url_action,
    text_block,
    two_columns,
)
from global_modules.teams.client import (
    TeamsNotificationError,
    send_card,
    send_payload,
    send_text,
)
from global_modules.teams.templates import alert_card, dag_failure_card, info_card

__all__ = [
    "TeamsNotificationError",
    "alert_card",
    "build_card",
    "dag_failure_card",
    "fact_set",
    "info_card",
    "notify_teams_on_failure",
    "open_url_action",
    "send_card",
    "send_payload",
    "send_text",
    "text_block",
    "two_columns",
]
