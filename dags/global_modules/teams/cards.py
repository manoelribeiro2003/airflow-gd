"""Primitivas de composição de Adaptive Cards para o Microsoft Teams.

Cada função retorna um dicionário novo: nada aqui muta a entrada, o que permite
compor blocos livremente e reaproveitar fragmentos entre templates.
"""

from global_modules.teams.redaction import redact_secrets

CARD_VERSION = "1.5"
CARD_SCHEMA = "https://adaptivecards.io/schemas/adaptive-card.json"
CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"

# Cores válidas do Adaptive Card, por nível de severidade.
COLOR_DEFAULT = "Default"
COLOR_GOOD = "Good"
COLOR_WARNING = "Warning"
COLOR_ATTENTION = "Attention"
COLOR_ACCENT = "Accent"

SEVERITY_COLORS = {
    "info": COLOR_ACCENT,
    "success": COLOR_GOOD,
    "warning": COLOR_WARNING,
    "error": COLOR_ATTENTION,
}

# Limite prático de payload do Teams (28 KB). Textos longos são truncados antes disso.
MAX_TEXT_LENGTH = 4000


def _to_camel_case(name: str) -> str:
    """Converte `horizontal_alignment` em `horizontalAlignment` (chaves do schema)."""
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


def _camel_props(props: dict) -> dict:
    """Converte as chaves snake_case dos kwargs para o camelCase do Adaptive Card."""
    return {_to_camel_case(key): value for key, value in props.items() if value is not None}


def truncate(text: str, limit: int = MAX_TEXT_LENGTH) -> str:
    """Trunca o texto preservando o início, que é a parte útil de um traceback."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _safe_text(value) -> str:
    """Mascara credenciais antes de truncar: o corte pode quebrar o padrão da senha."""
    return truncate(redact_secrets(str(value)))


def text_block(text: str, **props) -> dict:
    """Cria um TextBlock. Kwargs em snake_case viram camelCase (`size`, `weight`, `color`...)."""
    return {"type": "TextBlock", "text": _safe_text(text), "wrap": True, **_camel_props(props)}


def fact_set(facts: dict) -> dict:
    """Cria um FactSet a partir de um mapa rótulo -> valor.

    Substitui a sequência de TextBlocks repetidos usada nos cards antigos.
    """
    return {
        "type": "FactSet",
        "facts": [
            {"title": _safe_text(title), "value": _safe_text(value)}
            for title, value in facts.items()
        ],
    }


def column(items: list) -> dict:
    """Cria uma Column que ocupa o espaço disponível."""
    return {"type": "Column", "width": "stretch", "items": list(items)}


def two_columns(left: dict, right: dict, **props) -> dict:
    """Cria um ColumnSet com dois blocos lado a lado."""
    return {
        "type": "ColumnSet",
        "columns": [column([left]), column([right])],
        **_camel_props(props),
    }


def open_url_action(title: str, url: str) -> dict:
    """Cria um botão que abre uma URL externa."""
    return {"type": "Action.OpenUrl", "title": title, "url": url}


def build_card(title: str, body: list, color: str = COLOR_DEFAULT, actions: list = None) -> dict:
    """Monta o envelope completo da mensagem com um Adaptive Card anexado.

    O envelope `{"type": "message", "attachments": [...]}` é aceito tanto pelo
    Power Automate Workflow quanto pelo Incoming Webhook do Teams.
    """
    header = text_block(
        title,
        size="Large",
        weight="Bolder",
        color=color,
        horizontal_alignment="Center",
    )
    content = {
        "type": "AdaptiveCard",
        "version": CARD_VERSION,
        "$schema": CARD_SCHEMA,
        "body": [header, *body],
    }
    if actions:
        content["actions"] = list(actions)

    return {
        "type": "message",
        "attachments": [{"contentType": CARD_CONTENT_TYPE, "content": content}],
    }
