"""default_args padrão das DAGs: callback de falha no Teams, retry e timeout.

Centraliza a política para que ajustes (retry, timeout) sejam feitos num lugar só.

`execution_timeout` faz uma task travada (lock no SQL Server, ConnectorX sem resposta)
falhar e entrar no fluxo de retry/alerta, em vez de ficar em `running` indefinidamente.
45min cobre com folga a maior duração histórica das tasks (~18min); tasks que podem
passar disso sobrescrevem o valor no próprio `@task`. DAGs que ainda escrevem
o default_args à mão usam `DEFAULT_EXECUTION_TIMEOUT` diretamente.
"""

from datetime import datetime, timedelta
from types import MappingProxyType

from global_modules.teams import notify_teams_on_failure

DEFAULT_EXECUTION_TIMEOUT = timedelta(minutes=45)

STANDARD_DAG_ARGS = MappingProxyType({
    "on_failure_callback": notify_teams_on_failure,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
})

# Tasks que extraem do SharePoint via Graph API. O cliente não trata 429/Retry-After e o
# throttling costuma durar alguns minutos. Com backoff (e jitter do Airflow) as esperas ficam
# em 5-10, 10-20 e 20-30min, somando 35-60min entre as tentativas.
SHAREPOINT_EXTRACT_RETRY_ARGS = MappingProxyType({
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
})


def default_dag_args(owner: str, start_date: datetime, **overrides) -> dict:
    """Monta o default_args padrão; `overrides` substituem ou acrescentam chaves.

    Devolve um dict novo a cada chamada, pois o Airflow altera o default_args recebido.
    """
    return {
        "owner": owner,
        "start_date": start_date,
        **STANDARD_DAG_ARGS,
        **overrides,
    }
