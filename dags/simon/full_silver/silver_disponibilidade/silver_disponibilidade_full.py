import os
from datetime import datetime

import pandas as pd
from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.task_group import TaskGroup
from global_modules.dag_defaults import DEFAULT_EXECUTION_TIMEOUT
from global_modules.ms_teams import notify_teams_on_failure
from global_modules.mssql import get_mssql_url
from sqlalchemy import create_engine

server = "prod"
DB = "elipsedev" if server == "dev" else "elipse"
DW_CONN = "postgres_eng_server_dev" if server == "dev" else "postgres_eng_server"
EXTRACT_FILE_NAME = "extract_full.sql"

# Obter data e hora atual
data_hora_atual = (datetime.now()).strftime("%Y%m%d%H%M%S")

# Adicionar o range da carga
data_inicio = "2024-10-01 05:24:00"
data_inicio_formatado = datetime.strptime(data_inicio, "%Y-%m-%d %H:%M:%S").strftime(
    "%Y%m%d_%H%M%S"
)

data_fim = "2025-01-01 06:00:00"
data_fim_formatado = datetime.strptime(data_fim, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d_%H%M%S")

# Nome da conexão definida no Airflow Connections
connection_id_sob = "elipse_sob"
connection_id_for = "elipse_for"
connection_id_cra = "elipse_cra"


# reads the sql file and returns the query
def read_sql_file(file_path: str):
    _dir = os.path.dirname(os.path.abspath(__file__))
    sql_dir = os.path.join(_dir, f"sql_files/{file_path}")

    with open(sql_dir, "r", encoding="utf-8") as file:
        query = file.read()
    return query


default_args = {
    "owner": "yan arcanjo",
    "start_date": datetime(2025, 1, 26, 6, 5),
    "on_failure_callback": notify_teams_on_failure,
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
}


def extract_data_sob():
    print(f"a conexão escolhida é: {DW_CONN}")
    engine = create_engine(get_mssql_url(connection_id_sob))
    params = (
        data_inicio,
        data_fim,
        20,
    )  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(EXTRACT_FILE_NAME), engine, params=params)
    df["ID_Grupo"] = df["ID_Grupo"].astype("Int64")
    df["Cracha_Operador"] = df["Cracha_Operador"].astype("Int64")
    df["Cracha_Preparador"] = df["Cracha_Preparador"].astype("Int64")
    df["Cracha_Lider"] = df["Cracha_Lider"].astype("Int64")

    return df


def extract_data_for():
    engine = create_engine(get_mssql_url(connection_id_for))
    params = (
        data_inicio,
        data_fim,
        21,
    )  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(EXTRACT_FILE_NAME), engine, params=params)
    df["ID_Grupo"] = df["ID_Grupo"].astype("Int64")
    df["Cracha_Operador"] = df["Cracha_Operador"].astype("Int64")
    df["Cracha_Preparador"] = df["Cracha_Preparador"].astype("Int64")
    df["Cracha_Lider"] = df["Cracha_Lider"].astype("Int64")

    return df


def extract_data_cra():
    engine = create_engine(get_mssql_url(connection_id_cra))
    params = (
        data_inicio,
        data_fim,
        40,
    )  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(EXTRACT_FILE_NAME), engine, params=params)
    df["ID_Grupo"] = df["ID_Grupo"].astype("Int64")
    df["Cracha_Operador"] = df["Cracha_Operador"].astype("Int64")
    df["Cracha_Preparador"] = df["Cracha_Preparador"].astype("Int64")
    df["Cracha_Lider"] = df["Cracha_Lider"].astype("Int64")

    return df


def concat_data_and_load_temp(**kwargs):
    ti = kwargs["ti"]
    df_sob = ti.xcom_pull(task_ids="extract_all.extract_data_sob")
    df_cra = ti.xcom_pull(task_ids="extract_all.extract_data_cra")
    df_for = ti.xcom_pull(task_ids="extract_all.extract_data_for")

    df = pd.concat([df_sob, df_cra, df_for], ignore_index=True)

    df.drop(columns=["linha"])

    df = df.sort_values("E3TimeStamp").drop_duplicates(
        subset=["Id", "id_estabelecimento"], keep="last"
    )

    hook = PostgresHook(postgres_conn_id=DW_CONN)
    df.to_sql(
        "temp_paradas",
        hook.get_sqlalchemy_engine({"executemany_mode": "values"}),
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
    )


gold_dataset = Dataset("elipse://gold/f_disponibilidade_simon_full")

with DAG(
    "SILVER_F_DISPONIBILIDADE_SIMON_FULL",
    default_args=default_args,
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["elipse", "silver", "full"],
) as dag:
    with TaskGroup("extract_all") as extraction:
        extract_sob = PythonOperator(task_id="extract_data_sob", python_callable=extract_data_sob)
        extract_for = PythonOperator(task_id="extract_data_for", python_callable=extract_data_for)
        extract_cra = PythonOperator(task_id="extract_data_cra", python_callable=extract_data_cra)

        _ = [extract_sob, extract_for, extract_cra]

    concat_and_load = PythonOperator(
        task_id="concat_data_and_load_temp", python_callable=concat_data_and_load_temp
    )
    merge_data = SQLExecuteQueryOperator(
        task_id="merge_table_and_drop_temp",
        conn_id=DW_CONN,
        sql="./sql_files/merge_full.sql",
        params={"hora_inicio": data_inicio, "hora_fim": data_fim, "DB": DB},
        autocommit=True,
        outlets=[gold_dataset],
    )
    vacuum_task = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql=f"VACUUM {DB}.silver.oee_fparadas;",
        conn_id=DW_CONN,
        autocommit=True,  # Isso desabilita a transação para permitir o VACUUM
    )
    analyze_task = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql=f"ANALYZE {DB}.silver.oee_fparadas;",
        conn_id=DW_CONN,
        autocommit=True,
    )

_ = extraction >> concat_and_load >> vacuum_task >> analyze_task >> merge_data
