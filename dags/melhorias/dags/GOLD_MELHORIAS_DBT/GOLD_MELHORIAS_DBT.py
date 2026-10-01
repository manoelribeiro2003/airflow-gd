"""Orquestra o dbt de Melhorias (deps + build).

Disparada pelos Datasets bronze (aprovacao + ganhos), roda o dbt CLI sobre o
projeto em melhorias/dbt e emite o Dataset gold. Credencial vem da Airflow
Variable ENG_DATABASE_URL, quebrada em env vars DBT_* (ADR 0002).

O seed deixou de ser rodado pelo dbt: as tabelas mel_* auxiliares são carregadas
manualmente no SQL Server via DBeaver/SQL (ADR 0004). Por isso a task dbt_seed
está comentada e o build roda com --exclude resource_type:seed.

Nas retentativas da dbt_build roda `dbt retry` (só os nós que falharam) em vez de
um build inteiro; ver dbt_command.py (issue #8). Clear manual da task também conta
como retentativa (mesmo run_id): depois de corrigir um model, o Clear refaz só os
nós que falharam. Para rebuild completo, disparar uma nova run (Trigger DAG).
"""

import os
import subprocess
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from airflow import DAG, Dataset
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import get_current_context
from airflow.utils.log.logging_mixin import LoggingMixin
from global_modules.dag_defaults import default_dag_args
from global_modules.mssql import get_mssql_driver
from melhorias.dags.GOLD_MELHORIAS_DBT.dbt_command import RUN_ID_ENV_VAR, choose_dbt_command
from sqlalchemy.engine import make_url

log = LoggingMixin().log

# Disparado pela SILVER_MELHORIAS_DATA_FAP (emite data_fap) e pela
# SILVER_MELHORIAS_VOLUME_REAL (emite volume_real, que já depende de data_fap).
# Assim o dbt roda só depois do dt_fap e do volume real atualizados.
MEL_DATA_FAP_DATASET = Dataset("melhorias://silver/data_fap")
MEL_VOLUME_REAL_DATASET = Dataset("melhorias://silver/volume_real")
MEL_GOLD_DATASET = Dataset("melhorias://gold/melhorias")

# melhorias/dags/GOLD_MELHORIAS_DBT/ -> parents[2] = melhorias
DBT_PROJECT_DIR = Path(__file__).parents[2] / "dbt"
# target-path do dbt_project.yml; o dbt retry le o artefato da tentativa anterior daqui.
DBT_RUN_RESULTS = DBT_PROJECT_DIR / "target" / "run_results.json"


def _dbt_env() -> dict[str, str]:
    """Quebra ENG_DATABASE_URL (URL SQLAlchemy) nas env vars que o profiles.yml lê.

    O driver ODBC vem da Variable MSSQL_ODBC_DRIVER (global_modules.mssql).
    """
    raw = Variable.get("ENG_DATABASE_URL", None)
    if raw is None:
        raise ValueError("Variável do airflow 'ENG_DATABASE_URL' não foi definida.")

    url = make_url(raw)
    return {
        **os.environ,
        "DBT_HOST": url.host or "",
        "DBT_PORT": str(url.port or 1433),
        "DBT_DB": url.database or "dbengenharia",
        "DBT_USER": url.username or "",
        "DBT_PWD": url.password or "",
        "DBT_DRIVER": get_mssql_driver(),
    }


def _run_dbt(command: Sequence[str], extra_env: dict[str, str] | None = None) -> None:
    env = {**_dbt_env(), **(extra_env or {})}
    full = [
        "dbt",
        *command,
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
    ]
    log.info(f"[dbt] {' '.join(command)}")
    # Streama o stdout/stderr do dbt linha a linha pro logger do Airflow (aparece ao
    # vivo no log da task). subprocess.run nao capturava o fd do subprocesso, entao o
    # output do dbt nao entrava no task log.
    process = subprocess.Popen(  # noqa: S603
        full,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        log.info(line.rstrip())
    returncode = process.wait()
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, full)


@task
def dbt_deps():
    _run_dbt(["deps"])


# Seed desativado: as tabelas mel_* auxiliares passam a ser carregadas manualmente
# no SQL Server via DBeaver/SQL (ADR 0004). Os CSVs e o _seeds.yml continuam no
# projeto só como contrato de schema; os ref() resolvem para as tabelas dbo.mel_*
# criadas a mao. Reabilitar a task abaixo (e tirar o --exclude do build) caso o
# seed volte a ser gerenciado pelo dbt.
# @task
# def dbt_seed():
#     _run_dbt(["seed"])


@task(outlets=[MEL_GOLD_DATASET])
def dbt_build():
    # Falha deterministica (SQL/teste quebrado) nao melhora com build inteiro de novo:
    # a partir da 2a tentativa roda dbt retry sobre o run_results.json desta run.
    ti = get_current_context()["ti"]
    command = choose_dbt_command(ti.try_number, DBT_RUN_RESULTS, ti.run_id)
    log.info(f"[dbt] tentativa {ti.try_number}: dbt {command[0]}")
    # run_id vai para o metadata.env do run_results.json (prefixo DBT_ENV_CUSTOM_ENV_),
    # para a proxima tentativa saber que o artefato e desta run.
    _run_dbt(command, extra_env={RUN_ID_ENV_VAR: ti.run_id})


default_args = default_dag_args(owner="Antonio Albuquerque", start_date=datetime(2025, 1, 26, 6, 5))

with DAG(
    dag_id="GOLD_MELHORIAS_DBT",
    default_args=default_args,
    schedule=[MEL_DATA_FAP_DATASET, MEL_VOLUME_REAL_DATASET],
    catchup=False,
    max_active_runs=1,
    tags=["melhorias", "gold", "dbt"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    # dbt_seed() removido da cadeia (seed manual no SQL Server, ADR 0004).
    _ = start >> dbt_deps() >> dbt_build() >> end
