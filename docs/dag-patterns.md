# DAG Patterns Reference

## Idempotency

Tasks that process large data use two sentinel mechanisms from `global_modules/utils.py`:

- **Parquet sentinel** (`extract_data_{estab}.parquet`): If present, extraction is skipped. Created atomically via `.tmp` → rename (`get_parquet_file()`).
- **Step sentinel** (`{step_name}.finished`): If present, that step is skipped. Created via `sentinel.touch()` (`get_sentinel_file()`).

The step sentinel is written only after the step finishes, so a worker that dies in between makes the retry run the step again. A step that loads a stage table must produce the same stage when repeated; the preferred way is to clear it in the same transaction as the load (`replace_pg_table` from `global_modules/pg_load.py`). An unguarded append (`COPY`/`INSERT` with no prior clear) duplicates the stage and makes the following MERGE fail on every retry.

A final `clear_cache()` task deletes parquets and sentinels, resetting state for the next run. It is the last task in the chain with the default `trigger_rule` (`all_success`), so it only runs when every upstream task succeeds. If an upstream task fails terminally (after retries), `clear_cache()` is skipped and the sentinels are left on disk — see [Manual Cache Reset](#manual-cache-reset-admin_reset_sentinels).

## Manual Cache Reset (`ADMIN_RESET_SENTINELS`)

Sentinels and cache parquets live on the worker filesystem under `/opt/airflow/dags` (read-write volume), not in the Airflow metadata DB. Airflow's native "Clear task" resets task-instance state only — it does **not** remove these files. When a run fails terminally the orphaned `.finished` sentinel makes the next run skip a step and risk loading stale data.

`dags/admin/ADMIN_RESET_SENTINELS/` is a manual-trigger DAG (`schedule=None`) that removes orphaned `*.finished` sentinels and `*.parquet` cache files by globbing `/opt/airflow/dags`. It is param-driven:

| Param | Default | Effect |
|---|---|---|
| `target` | `""` | Substring of the DAG's relative path (e.g. `CICLOS`). Empty = all DAGs. |
| `dry_run` | `true` | `true` only logs what would be deleted; `false` deletes. |
| `include_parquet` | `true` | Also remove `*.parquet` cache files, not just sentinels. |

Recommended flow: trigger with `dry_run=true`, inspect the `reset_cache` task log, then re-trigger with `dry_run=false`. Guard is intentionally light (`max_active_runs=1` + a log warning) — ensure no target DAG is running before deleting, since removing a sentinel mid-run can cause double execution.

## Legacy Dependency Pattern (`CustomSqlSensor`)

Older DAGs use `CustomSqlSensor` with `wait_dependencies.sql` from `global_files/sql_files/`. The sensor checks `start_date` in the Airflow metadata DB via a Jinja-templated query, polling every 2 minutes with a 1-hour timeout.

New DAGs should use Dataset-based scheduling instead.

## Dataset-Based Scheduling

Silver DAGs declare a `Dataset` outlet:

```python
from airflow.datasets import Dataset

MY_DATASET = Dataset("my_dataset_uri")

@dag(..., outlets=[MY_DATASET])
def dag_factory():
    ...
```

Gold DAGs consume it:

```python
@dag(..., schedule=[MY_DATASET])
def dag_factory():
    ...
```

This removes the need for polling sensors and makes dependencies explicit in the Airflow UI.
