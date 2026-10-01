from typing import Literal

from airflow.models import Variable

type EnvOptions = Literal[
    "SHAREPOINT_SITE_URL",
    "SHAREPOINT_CLIENT_ID",
    "SHAREPOINT_CLIENT_SECRET",
    "SHAREPOINT_LIST_NAME",
    "SHAREPOINT_TENANT_ID",
    "ENG_DATABASE_URL",
    "SHAREPOINT_USERNAME",
    "SHAREPOINT_USER_PASSWORD",
    "SHAREPOINT_SEARCH_DAYS",
]


def env(env_name: EnvOptions) -> str:
    value = Variable.get(env_name, None)

    if value is None:
        raise ValueError(f"Variável do Airflow '{env_name}' não definida.")

    return value


def get_sharepoint_search_days(default: int = 90) -> int:
    """Janela (em dias) de extração do SharePoint. Vem da Variable
    `SHAREPOINT_SEARCH_DAYS`; se ausente, usa `default`. Mesma fonte alimenta o
    `timedelta` do fetch e o DELETE do merge, garantindo que as janelas batam."""
    value = Variable.get("SHAREPOINT_SEARCH_DAYS", default)

    if not str(value).isdigit():
        raise ValueError("Variável do Airflow 'SHAREPOINT_SEARCH_DAYS' deve ser int.")

    return int(value)
