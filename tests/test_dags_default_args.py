"""Caracterização: o default_args efetivo das DAGs com a política padrão.

Carrega o DagBag real e garante que o default_args de cada DAG listada é
exatamente owner + start_date + política padrão, sem chave a mais nem a menos,
e que cada task herda o `execution_timeout` padrão ou tem override explícito.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from airflow.models import DagBag
from airflow.utils.timezone import convert_to_utc
from global_modules.teams import notify_teams_on_failure

DAGS_FOLDER = Path(__file__).resolve().parent.parent / "dags"

# Variables lidas no topo de módulo por algumas DAGs; valor fictício só para o parse.
PARSE_TIME_VARIABLES = ("DDB_PG_FLAKEFLOW_CONN", "CX_FLAKEFLOW_CONN")

DEFAULT_EXECUTION_TIMEOUT = timedelta(minutes=45)

STANDARD_DAG_ARGS = {
    "on_failure_callback": notify_teams_on_failure,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
}

# Política das tasks que extraem do SharePoint: cobre throttling (429) da Graph API,
# que costuma durar alguns minutos. Issue #7.
SHAREPOINT_EXTRACT_RETRY_ARGS = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}

# Funções do cliente em global_modules.sharepoint.sharepoint que chamam a Graph/SharePoint.
SHAREPOINT_CLIENT_FUNCTIONS = frozenset({
    "fetch_sharepoint_items",
    "fetch_sharepoint_items_with_graph_api",
    "download_sharepoint_file_with_graph_api",
})

SHAREPOINT_EXTRACT_TASKS = {
    ("BRONZE_MELHORIA_APROVACAO", "extract_sharepoint"),
    ("BRONZE_MELHORIA_GANHOS", "extract_sharepoint"),
    ("SILVER_MELHORIAS_VOLUME_REAL", "extract_sharepoint"),
}

ANTONIO = "Antonio Albuquerque"
YAN = "yan arcanjo"

EXPECTED_OWNER_AND_START = {
    "BRONZE_F_AREA": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_F_ELIMINACAO_FERRAMETAL": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_F_EVENTOS": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_F_FL_NOTA_FISCAL": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_F_PRODUTOS_RELACIONADOS": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_F_SKU": (ANTONIO, datetime(2025, 1, 26, 7, 0)),
    "BRONZE_MELHORIA_APROVACAO": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "BRONZE_MELHORIA_GANHOS": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "BRONZE_MELHORIA_DATA_FAP": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "SILVER_MELHORIAS_VOLUME_REAL": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "GOLD_MELHORIAS_DBT": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "NOTIFY_SHAREPOINT_SECRET_EXPIRY": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "AIRFLOW_LOG_CLEANUP": (ANTONIO, datetime(2026, 4, 1)),
    "AIRFLOW_DB_CLEANUP": (ANTONIO, datetime(2026, 9, 1)),
    "STG_ELIPSE_OEE_PRODUTO": (ANTONIO, datetime(2025, 1, 26, 6, 5)),
    "GOLD_ELIPSE_DMAQUINAS": ("yan.arcanjo", datetime(2022, 8, 18, 7, 0)),
    "GOLD_ELIPSE_FAPOIO": ("yan_arcanjo", datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_DISPONIBILIDADE_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_PERFORMANCE_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_QUALIDADE_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_DISPONIBILIDADE_SIMON_FULL": (YAN, datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_PERFORMANCE_SIMON_FULL": (YAN, datetime(2025, 1, 26, 6, 5)),
    "GOLD_F_QUALIDADE_SIMON_FULL": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_D_FABRICAS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_D_FAMILIAS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_D_MAQUINAS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_D_MOTIVOS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_D_SETORES_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_ELIPSE_FAPOIO": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_F_CICLOS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_F_DISPONIBILIDADE_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_F_PERFORMANCE_SIMON": (YAN, datetime(2025, 2, 21, 6, 5)),
    "SILVER_F_PRODUTOS_SIMON": (YAN, datetime(2025, 1, 26, 6, 5)),
    "SILVER_F_QUALIDADE_SIMON": (YAN, datetime(2025, 2, 21, 6, 5)),
    "F_SIMON_SEGMENTACAO": (YAN, datetime(2024, 6, 30, 7, 0)),
}


@pytest.fixture(scope="module")
def dagbag():
    with pytest.MonkeyPatch.context() as mp:
        for name in PARSE_TIME_VARIABLES:
            mp.setenv(f"AIRFLOW_VAR_{name}", "postgresql://parse:parse@localhost/parse")
        yield DagBag(dag_folder=str(DAGS_FOLDER), include_examples=False)


def test_dagbag_sem_erros_de_import(dagbag):
    assert dagbag.import_errors == {}


@pytest.mark.parametrize("dag_id", sorted(EXPECTED_OWNER_AND_START))
def test_default_args_efetivo_preservado(dagbag, dag_id):
    owner, start_date = EXPECTED_OWNER_AND_START[dag_id]
    args = dagbag.dags[dag_id].default_args

    # O DAG converte start_date naive para UTC usando o fuso padrão configurado.
    assert args == {
        "owner": owner,
        "start_date": convert_to_utc(start_date),
        **STANDARD_DAG_ARGS,
    }


# Tasks cuja duração histórica fica perto do padrão (ou varia com Variable/janela)
# e por isso sobrescrevem o timeout. Levantamento registrado no MR da issue #5.
EXECUTION_TIMEOUT_OVERRIDES = {
    ("BRONZE_F_FL_NOTA_FISCAL", "extract_window"): timedelta(hours=1),
    ("SILVER_F_CICLOS_SIMON", "extract_data_sob"): timedelta(minutes=90),
    ("SILVER_F_CICLOS_SIMON", "extract_data_for"): timedelta(minutes=90),
    ("SILVER_F_CICLOS_SIMON", "extract_data_cra"): timedelta(minutes=90),
    ("STG_ELIPSE_OEE_PRODUTO", "extract_data_sob"): timedelta(minutes=90),
    ("STG_ELIPSE_OEE_PRODUTO", "extract_data_for"): timedelta(minutes=90),
    ("STG_ELIPSE_OEE_PRODUTO", "extract_data_cra"): timedelta(minutes=90),
}


def test_overrides_de_timeout_apontam_para_tasks_existentes(dagbag):
    missing = [
        (dag_id, task_id)
        for dag_id, task_id in EXECUTION_TIMEOUT_OVERRIDES
        if not dagbag.dags[dag_id].has_task(task_id)
    ]

    assert missing == []


def test_toda_task_tem_execution_timeout_padrao_ou_override(dagbag):
    # Cobre todas as DAGs, inclusive as que ainda escrevem default_args à mão.
    actual = {
        (dag_id, task.task_id): task.execution_timeout
        for dag_id, dag in dagbag.dags.items()
        for task in dag.tasks
    }

    assert actual == {
        key: EXECUTION_TIMEOUT_OVERRIDES.get(key, DEFAULT_EXECUTION_TIMEOUT) for key in actual
    }


def _calls_sharepoint_client(task) -> bool:
    code = getattr(getattr(task, "python_callable", None), "__code__", None)
    return code is not None and not SHAREPOINT_CLIENT_FUNCTIONS.isdisjoint(code.co_names)


def test_tasks_que_chamam_sharepoint_estao_registradas(dagbag):
    # Nova task que chama o cliente do SharePoint precisa entrar em SHAREPOINT_EXTRACT_TASKS.
    actual = {
        (dag_id, task.task_id)
        for dag_id, dag in dagbag.dags.items()
        for task in dag.tasks
        if _calls_sharepoint_client(task)
    }

    assert actual == SHAREPOINT_EXTRACT_TASKS


@pytest.mark.parametrize(("dag_id", "task_id"), sorted(SHAREPOINT_EXTRACT_TASKS))
def test_extract_sharepoint_tolera_throttling(dagbag, dag_id, task_id):
    task = dagbag.dags[dag_id].get_task(task_id)

    assert {key: getattr(task, key) for key in SHAREPOINT_EXTRACT_RETRY_ARGS} == (
        SHAREPOINT_EXTRACT_RETRY_ARGS
    )
