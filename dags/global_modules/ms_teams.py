"""Compatibilidade com os imports anteriores ao pacote `global_modules.teams`.

A implementação vive em `global_modules/teams/`. Este módulo existe apenas para
que as DAGs que já importam `notify_teams_on_failure` e `send_teams_message`
continuem funcionando sem alteração.
"""

from global_modules.teams.callbacks import notify_teams_on_failure
from global_modules.teams.client import TeamsNotificationError, send_text

__all__ = [
    "TeamsNotificationError",
    "notify_teams_on_failure",
    "send_teams_message",
]


def send_teams_message(message: str) -> None:
    """Envia uma mensagem de texto puro para o canal do Teams.

    :param message: A mensagem a ser enviada.
    """
    send_text(message)
