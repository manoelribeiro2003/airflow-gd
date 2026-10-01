from datetime import datetime

from airflow.decorators import dag
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from global_modules.dag_defaults import default_dag_args

RETENTION_DAYS = 90

default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2026, 9, 1))

# `airflow db clean` sempre preserva o ultimo dag_run agendado de cada DAG, entao
# nao quebra a continuidade do agendamento. --skip-archive apaga de fato em vez de
# copiar para tabelas _airflow_deleted__* (que manteriam o espaco ocupado).
DB_CLEAN_COMMAND = """
{%- set cutoff = data_interval_end - macros.timedelta(days=params.retention_days) %}
set -euo pipefail
airflow db clean \\
    --clean-before-timestamp "{{ cutoff.isoformat() }}" \\
    --skip-archive \\
    --verbose \\
    --yes {{ '--dry-run' if params.dry_run else '' }}
"""


@dag(
    dag_id="AIRFLOW_DB_CLEANUP",
    default_args=default_args,
    schedule="0 3 * * 0",  # domingo 03:00
    catchup=False,
    max_active_runs=1,
    tags=["maintenance"],
    params={
        "retention_days": Param(
            RETENTION_DAYS,
            type="integer",
            minimum=30,
            description="Apaga registros de metadados mais antigos que N dias.",
        ),
        "dry_run": Param(
            False,
            type="boolean",
            description="Apenas lista o que seria apagado, sem remover nada.",
        ),
    },
)
def dag_factory():
    BashOperator(
        task_id="db_clean",
        bash_command=DB_CLEAN_COMMAND,
    )


dag_factory()
