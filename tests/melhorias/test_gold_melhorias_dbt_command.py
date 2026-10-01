"""Testes da escolha do comando dbt por tentativa na GOLD_MELHORIAS_DBT (issue #8)."""

import json

import pytest
from melhorias.dags.GOLD_MELHORIAS_DBT.dbt_command import choose_dbt_command

RUN_ID = "scheduled__2026-09-26T09:05:00+00:00"
BUILD = ("build", "--exclude", "resource_type:seed", "--indirect-selection", "cautious")
RETRY = ("retry",)


def _run_results(tmp_path, *statuses, run_id=RUN_ID):
    # Recorte do run_results.json real do dbt 1.8: so os campos que a escolha le.
    results = [{"unique_id": f"model.melhorias.m{i}", "status": s} for i, s in enumerate(statuses)]
    path = tmp_path / "run_results.json"
    path.write_text(
        json.dumps({
            "metadata": {"env": {"AIRFLOW_RUN_ID": run_id}},
            "args": {"which": "build"},
            "results": results,
        })
    )
    return path


def test_primeira_tentativa_roda_build_mesmo_com_artefato_retentavel(tmp_path):
    # Build novo sempre comeca do zero, mesmo com falha desta run no target/.
    path = _run_results(tmp_path, "error")

    assert choose_dbt_command(1, path, RUN_ID) == BUILD


@pytest.mark.parametrize("try_number", [2, 3])
def test_retentativa_com_falha_da_mesma_run_roda_retry(tmp_path, try_number):
    path = _run_results(tmp_path, "success", "error", "skipped")

    assert choose_dbt_command(try_number, path, RUN_ID) == RETRY


def test_retentativa_sem_run_results_cai_para_build(tmp_path):
    # Tentativa 1 falhou antes do dbt gravar o artefato (ex.: Variable ausente).
    assert choose_dbt_command(2, tmp_path / "run_results.json", RUN_ID) == BUILD


def test_retentativa_com_run_results_de_outra_run_cai_para_build(tmp_path):
    # Artefato velho de uma run anterior: dbt retry reprocessaria o estado errado.
    path = _run_results(tmp_path, "error", run_id="scheduled__2026-09-25T09:05:00+00:00")

    assert choose_dbt_command(2, path, RUN_ID) == BUILD


def test_retentativa_sem_no_falhado_cai_para_build(tmp_path):
    # Task limpa manualmente depois de um build ok: dbt retry nao faria nada.
    path = _run_results(tmp_path, "success", "pass", "warn")

    assert choose_dbt_command(2, path, RUN_ID) == BUILD


@pytest.mark.parametrize("content", ["", "{not json", "[]", '{"metadata": {}}'])
def test_retentativa_com_run_results_corrompido_cai_para_build(tmp_path, content):
    # Processo morto no meio da escrita, ou schema diferente do esperado.
    path = tmp_path / "run_results.json"
    path.write_text(content)

    assert choose_dbt_command(2, path, RUN_ID) == BUILD
