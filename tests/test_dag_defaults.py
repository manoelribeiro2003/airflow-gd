"""Testes do default_args padrão compartilhado pelas DAGs."""

from datetime import datetime, timedelta

from global_modules.dag_defaults import STANDARD_DAG_ARGS, default_dag_args
from global_modules.teams import notify_teams_on_failure

START = datetime(2025, 1, 26, 6, 5)


def test_default_dag_args_aplica_politica_padrao():
    assert default_dag_args(owner="fulano", start_date=START) == {
        "owner": "fulano",
        "start_date": START,
        "on_failure_callback": notify_teams_on_failure,
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
        "execution_timeout": timedelta(minutes=45),
    }


def test_default_dag_args_aceita_overrides():
    args = default_dag_args(owner="fulano", start_date=START, retries=0)

    assert args["retries"] == 0
    assert args["retry_delay"] == timedelta(minutes=2)


def test_default_dag_args_aceita_override_de_execution_timeout():
    args = default_dag_args(owner="fulano", start_date=START, execution_timeout=timedelta(hours=1))

    assert args["execution_timeout"] == timedelta(hours=1)


def test_default_dag_args_aceita_chaves_extras():
    args = default_dag_args(owner="fulano", start_date=START, email_on_retry=False)

    assert args["email_on_retry"] is False


def test_default_dag_args_devolve_dict_novo_a_cada_chamada():
    primeiro = default_dag_args(owner="fulano", start_date=START)
    primeiro["retries"] = 99

    novo = default_dag_args(owner="fulano", start_date=START)

    assert novo["retries"] == STANDARD_DAG_ARGS["retries"]
