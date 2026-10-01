"""Testes de integracao do `copy_to_stage` da SILVER_F_CICLOS_SIMON (issue #10).

Um retry depois de o COPY terminar e antes da sentinela ser gravada nao pode
duplicar o stage. Precisam de um Postgres real apontado por TEST_PG_URI (ver
tests/test_pg_load.py); sem a variavel, sao pulados.
"""

import importlib.util
import os
import uuid
from pathlib import Path

import duckdb as ddb
import pytest

PG_URI = os.environ.get("TEST_PG_URI")

pytestmark = pytest.mark.skipif(not PG_URI, reason="TEST_PG_URI nao definida")

DAG_FILE = (
    Path(__file__).resolve().parent.parent
    / "dags/simon/silver/SILVER_F_ELIPSE_CICLOS/SILVER_F_ELIPSE_CICLOS.py"
)

MERGED_IDS = [10, 11, 12]


def _load_dag_module():
    spec = importlib.util.spec_from_file_location("silver_f_elipse_ciclos", DAG_FILE)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pg(sql: str) -> None:
    with ddb.connect() as con:
        con.execute(f"ATTACH '{PG_URI}' AS pg (TYPE POSTGRES)")
        con.execute(f"CALL postgres_execute('pg', '{sql}')")


def _ids(table: str) -> list[int]:
    with ddb.connect() as con:
        con.execute(f"ATTACH '{PG_URI}' AS pg (TYPE POSTGRES, READ_ONLY)")
        return [r[0] for r in con.execute(f"SELECT id FROM pg.{table} ORDER BY id").fetchall()]


@pytest.fixture
def stage_table():
    schema = f"test_stage_{uuid.uuid4().hex[:8]}"
    name = f"{schema}.stage_ciclos"
    _pg(f"CREATE SCHEMA {schema}; CREATE TABLE {name} (id int)")
    yield name
    _pg(f"DROP SCHEMA {schema} CASCADE")


@pytest.fixture
def dag_module(tmp_path, monkeypatch, stage_table):
    # global_modules.database le esta Variable no import; valor ficticio so para o parse.
    monkeypatch.setenv("AIRFLOW_VAR_ENG_DATABASE_URL", "mssql://parse:parse@localhost/parse")
    module = _load_dag_module()

    merged_file = tmp_path / "extract_data_merged.parquet"
    with ddb.connect() as con:
        con.execute(f"COPY (SELECT unnest({MERGED_IDS}) AS id) TO '{merged_file}' (FORMAT PARQUET)")

    monkeypatch.setattr(module, "STAGE_TABLE", stage_table)
    monkeypatch.setattr(module, "get_duckdb_conn", lambda _conn: PG_URI)
    monkeypatch.setattr(module, "_get_merged_parquet", lambda: merged_file)
    monkeypatch.setattr(module, "_get_sentinel", lambda name: tmp_path / f"{name}.finished")
    return module


def test_copy_to_stage_repetido_sem_sentinela_nao_duplica(dag_module, stage_table, tmp_path):
    copy_to_stage = dag_module.copy_to_stage.function

    copy_to_stage()
    first = _ids(stage_table)
    # Worker morreu depois do COPY e antes da sentinela: o retry roda de novo.
    (tmp_path / "copy_to_stage.finished").unlink()
    copy_to_stage()

    assert first == MERGED_IDS
    assert _ids(stage_table) == first


def test_copy_to_stage_descarta_lixo_anterior_do_stage(dag_module, stage_table):
    _pg(f"INSERT INTO {stage_table} VALUES (1), (2)")

    dag_module.copy_to_stage.function()

    assert _ids(stage_table) == MERGED_IDS


def test_copy_to_stage_com_sentinela_nao_toca_o_stage(dag_module, stage_table, tmp_path):
    _pg(f"INSERT INTO {stage_table} VALUES (1)")
    (tmp_path / "copy_to_stage.finished").touch()

    dag_module.copy_to_stage.function()

    assert _ids(stage_table) == [1]


def test_copy_to_stage_grava_sentinela(dag_module, tmp_path):
    dag_module.copy_to_stage.function()

    assert (tmp_path / "copy_to_stage.finished").exists()
