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

# Obter data e hora atual
data_hora_atual = (datetime.now()).strftime("%Y%m%d%H%M%S")

# Adicionar o range da carga
data_inicio = "2025-01-01 05:25:00"
data_inicio_formatado = datetime.strptime(data_inicio, "%Y-%m-%d %H:%M:%S").strftime(
    "%Y%m%d_%H%M%S"
)

data_fim = "2025-02-01 05:25:00"
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
    "start_date": datetime(2025, 2, 21, 6, 5),
    "on_failure_callback": notify_teams_on_failure,
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
}

extraction_sql = "full_silver_qualidade.sql"


def extract_data_sob():
    hook = create_engine(get_mssql_url(connection_id_sob))
    params = (20, data_inicio, data_fim)  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(extraction_sql), hook, params=params)

    return df


def extract_data_for():
    hook = create_engine(get_mssql_url(connection_id_for))
    params = (21, data_inicio, data_fim)  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(extraction_sql), hook, params=params)

    return df


def extract_data_cra():
    hook = create_engine(get_mssql_url(connection_id_cra))
    params = (40, data_inicio, data_fim)  # id_estabelecimento
    df = pd.read_sql_query(read_sql_file(extraction_sql), hook, params=params)

    return df


def concat_data_and_load_temp(**kwargs):
    ti = kwargs["ti"]
    df_sob = ti.xcom_pull(task_ids="extract_all.extract_data_sob")
    df_cra = ti.xcom_pull(task_ids="extract_all.extract_data_cra")
    df_for = ti.xcom_pull(task_ids="extract_all.extract_data_for")

    df = pd.concat([df_sob, df_cra, df_for], ignore_index=True)

    df = df.drop(columns=["linha"])

    df = df.sort_values("E3TimeStamp").drop_duplicates(
        subset=["E3TimeStamp", "Maquina_ID", "id_estabelecimento"], keep="last"
    )

    hook = PostgresHook(postgres_conn_id="postgres_eng_server")
    df.to_sql(
        "temp_qualidade",
        hook.get_sqlalchemy_engine({"executemany_mode": "values"}),
        schema="silver",
        if_exists="replace",
        index=False,
        chunksize=5000,
    )


gold_dataset = Dataset("elipse://gold/f_qualidade_simon_full")

with DAG(
    "SILVER_F_QUALIDADE_SIMON_FULL",
    default_args=default_args,
    schedule=None,
    catchup=False,
    max_active_runs=1,
) as dag:
    with TaskGroup("extract_all") as extraction:
        extract_sob = PythonOperator(task_id="extract_data_sob", python_callable=extract_data_sob)
        extract_for = PythonOperator(task_id="extract_data_for", python_callable=extract_data_for)
        extract_cra = PythonOperator(task_id="extract_data_cra", python_callable=extract_data_cra)

        _ = [extract_sob, extract_for, extract_cra]

    concat_and_load = PythonOperator(
        task_id="concat_data_and_load_temp",
        python_callable=concat_data_and_load_temp,
    )

    merge_data = SQLExecuteQueryOperator(
        task_id="merge_table_and_drop_temp",
        conn_id="postgres_eng_server",
        sql="./sql_files/full_merge_silver_qualidade.sql",
        parameters={"data_inicio": data_inicio, "data_fim": data_fim},
        autocommit=True,
        outlets=[gold_dataset],
    )

    vacuum_task = SQLExecuteQueryOperator(
        task_id="vacuum_task",
        sql="VACUUM elipse.silver.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,  # Isso desabilita a transação para permitir o VACUUM
    )

    analyze_task = SQLExecuteQueryOperator(
        task_id="analyze_task",
        sql="ANALYZE elipse.silver.oee_fqualidade;",
        conn_id="postgres_eng_server",
        autocommit=True,
    )


_ = extraction >> concat_and_load >> vacuum_task >> analyze_task >> merge_data
