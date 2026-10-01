"""Driver ODBC do SQL Server centralizado na Airflow Variable MSSQL_ODBC_DRIVER.

Ler so em tempo de execucao da task (nunca no topo do modulo da DAG), para nao
consultar o metadata DB a cada parse.
"""

from airflow.hooks.base import BaseHook
from airflow.models import Variable
from sqlalchemy.engine import URL, make_url

MSSQL_DRIVER_VAR = "MSSQL_ODBC_DRIVER"
# Unico driver instalado na imagem (Dockerfile: msodbcsql17).
DEFAULT_MSSQL_DRIVER = "ODBC Driver 17 for SQL Server"
PYODBC_DIALECT = "mssql+pyodbc"


def get_mssql_driver() -> str:
    return Variable.get(MSSQL_DRIVER_VAR, DEFAULT_MSSQL_DRIVER)


def with_mssql_driver(url: str | URL) -> URL:
    """Troca o `driver` de uma URL mssql+pyodbc pelo driver central; outras URLs passam intactas."""
    parsed = make_url(url)
    if parsed.drivername != PYODBC_DIALECT:
        return parsed

    return parsed.update_query_dict({"driver": get_mssql_driver()})


def get_mssql_url(conn_id: str) -> URL:
    """Monta a URL SQLAlchemy de uma Airflow Connection SQL Server (credenciais escapadas)."""
    conn = BaseHook.get_connection(conn_id)

    return URL.create(
        PYODBC_DIALECT,
        username=conn.login,
        password=conn.password,
        host=conn.host,
        database=conn.schema,
        query={"driver": get_mssql_driver()},
    )
