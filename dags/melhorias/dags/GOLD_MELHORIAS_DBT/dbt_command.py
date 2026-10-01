"""Escolhe o comando dbt de cada tentativa da task dbt_build (issue #8)."""

import json
from pathlib import Path

# --exclude resource_type:seed: dbt build roda seed por padrao; excluimos para
# nao recarregar os CSVs (seed agora e manual, ADR 0004).
# --indirect-selection cautious: no modo padrao (eager) o --exclude leva junto todo
# teste que le um seed, e os testes singulares que cruzam seed com fonte nao rodavam
# (ADR 0013). Com cautious so sai o teste cujos pais sao todos seeds.
BUILD_COMMAND = (
    "build",
    "--exclude",
    "resource_type:seed",
    "--indirect-selection",
    "cautious",
)
RETRY_COMMAND = ("retry",)

# O dbt grava em metadata.env do run_results.json toda env var com o prefixo
# DBT_ENV_CUSTOM_ENV_ (sem o prefixo). Serve para saber de qual DAG run e o artefato.
RUN_ID_METADATA_KEY = "AIRFLOW_RUN_ID"
RUN_ID_ENV_VAR = f"DBT_ENV_CUSTOM_ENV_{RUN_ID_METADATA_KEY}"

# Mesmo conjunto que o dbt retry reexecuta (dbt.task.retry.RETRYABLE_STATUSES, 1.8).
# Revisar ao subir o dbt de versao (pyproject fixa <1.9).
RETRYABLE_STATUSES = frozenset({"error", "fail", "skipped", "runtime error"})


def _is_retryable_artifact(run_results_path: Path, run_id: str) -> bool:
    """True se o run_results.json e desta DAG run e tem no para o dbt retry refazer.

    Artefato ausente, ilegivel, de outra run ou sem falha conta como nao utilizavel.
    """
    try:
        run_results = json.loads(run_results_path.read_text(encoding="utf-8"))
        if run_results["metadata"]["env"].get(RUN_ID_METADATA_KEY) != run_id:
            return False
        return any(result["status"] in RETRYABLE_STATUSES for result in run_results["results"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def choose_dbt_command(try_number: int, run_results_path: Path, run_id: str) -> tuple[str, ...]:
    """Tentativa 1 roda build; as seguintes rodam retry se houver artefato utilizavel.

    dbt retry reexecuta so os nos com erro/falha/skip do run_results.json anterior,
    reaproveitando os args do build (inclusive o --exclude resource_type:seed e o
    --indirect-selection cautious).
    """
    if try_number > 1 and _is_retryable_artifact(run_results_path, run_id):
        return RETRY_COMMAND
    return BUILD_COMMAND
