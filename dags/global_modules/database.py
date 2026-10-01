from functools import cache
from typing import Literal

from airflow.models import Variable
from global_modules.mssql import with_mssql_driver
from global_modules.sharepoint.logs import log_message
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ENG_DATABASE_URL = Variable.get("ENG_DATABASE_URL", None)

type Estabelecimento = Literal["sob", "cra", "for"]
type ConnectorxVars = Literal["sob", "cra", "for", "pg", "flakeflow"]
type DuckdbVars = Literal["pg", "pg_flakeflow", "dbengenharia"]

CONNECTIONS_VAR: dict[Estabelecimento, str] = {
    "sob": "elipse_sob",
    "for": "elipse_for",
    "cra": "elipse_cra",
}


CX_CONNECTIONS_VAR: dict[ConnectorxVars, str] = {
    "sob": "CX_ELIPSE_SOB",
    "for": "CX_ELIPSE_FOR",
    "cra": "CX_ELIPSE_CRA",
    "pg": "CX_ELIPSE_PG",
    "flakeflow": "CX_FLAKEFLOW_CONN",
}

DUCKDB_CONNECTIONS_VAR: dict[DuckdbVars, str] = {
    "pg": "DDB_PG_CONN",
    "pg_flakeflow": "DDB_PG_FLAKEFLOW_CONN",
    "dbengenharia": "DDB_DB_ENGENHARIA_CONN",
}

ESTAB_CODE: dict[Estabelecimento, int] = {
    "sob": 20,
    "for": 21,
    "cra": 40,
}


@cache
def _get_var(conn: str) -> str:
    string_conn = Variable.get(conn, None)
    if string_conn is None:
        raise ValueError(f"Variável do airflow '{conn}' não foi definida.")

    return string_conn


def get_estab_code(estab: Estabelecimento):
    return ESTAB_CODE[estab]


def get_elipse_conn(
    estab: Estabelecimento,
    fast_executemany=False,
    use_setinputsizes=False,
) -> Engine:
    string_conn = _get_var(CONNECTIONS_VAR[estab])

    return create_engine(
        with_mssql_driver(string_conn),
        fast_executemany=fast_executemany,
        use_setinputsizes=use_setinputsizes,
    )  # pyright: ignore[reportReturnType]


def get_cx_conn(conn: ConnectorxVars):
    string_conn = _get_var(CX_CONNECTIONS_VAR[conn])

    return string_conn


def get_duckdb_conn(conn: DuckdbVars):
    string_conn = _get_var(DUCKDB_CONNECTIONS_VAR[conn])

    return string_conn


def get_eng_conn(fast_executemany=False, use_setinputsizes=True) -> Engine:
    if ENG_DATABASE_URL is None:
        raise ValueError("Variável do airflow 'ENG_DATABASE_URL' não foi definida.")

    return create_engine(
        with_mssql_driver(ENG_DATABASE_URL),
        fast_executemany=fast_executemany,
        use_setinputsizes=use_setinputsizes,
    )  # pyright: ignore[reportReturnType]


def exec_query_eng_db(query: str, params: dict | None = None):
    log_message(f"⚠️ Executando query '{query}'.")
    with get_eng_conn().begin() as conn:  # type: ignore
        conn.execute(text(query), params or {})  # type: ignore
        # conn.commit()
    log_message("✅ Query finalizada.")


def exec_merge(store_procedure: str):
    with get_eng_conn().begin() as conn:  # type: ignore
        conn.execute(text(f"EXEC {store_procedure}"))  # type: ignore
        # conn.commit()
    log_message(f"✅ Merge concluído para '{store_procedure}'.")


def get_ciclos_search_window() -> int:
    value = Variable.get("SILVER_F_CICLOS_DAYS_TO_SEARCH", None)
    if value is None:
        raise ValueError("Variável do airflow 'SILVER_F_CICLOS_DAYS_TO_SEARCH' não foi definida.")

    if not str(value).isdigit():
        raise ValueError("Variável do airflow 'SILVER_F_CICLOS_DAYS_TO_SEARCH' deve ser int.")

    return int(value)
