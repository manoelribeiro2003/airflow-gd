# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

projeto usa `glab`

## Commands

All tasks are run via [taskipy](https://github.com/taskipy/taskipy) through `uv`:

```bash
uv run task lint | format | lint-sql | format-sql | docker | build | push
uv run task test   # roda lint ANTES; gera htmlcov/
uv run task dw     # docker compose up --watch; roda build ANTES
```

Run a single test file:
```bash
uv run pytest -s -x -vv path/to/test_file.py
```

Initial setup:
```bash
cp .env.example .env   # fill in AIRFLOW_UID (id -u), DRIVER_PATH, DOCKER_REGISTRY, SharePoint creds
uv sync --group dev
```

## Architecture

CeleryExecutor + Redis + PostgreSQL, via Docker Compose (`docker-compose.yml`). Custom image (`Dockerfile`) on `apache/airflow:2.10.5` with MS SQL Server ODBC drivers (`msodbcsql17`) and TLS downgrade (`openssl.cnf`). Timezone: `America/Fortaleza`. UI: `http://localhost:8080`.

### SQL Server topology (versions differ per database)

| Database(s) | Version | Notes |
|---|---|---|
| `dbengenharia` | SQL Server **2019** Standard (15.0.4261.1) | dbt melhorias views target; has batch mode + columnstore |
| `elipse`, `sob`, `for`, `cra` | SQL Server **2008 R2 SP3** Standard (10.50.6529.0) | Legacy sources; require the `openssl.cnf` TLS downgrade (SECLEVEL=0) for ODBC Driver 17 to connect — this config is NOT dead. No batch mode/columnstore. |

DAGs implement **Bronze → Silver → Gold** medallion architecture for **SiMOn** (Sistema de Monitoramento Online):

| Layer | Paths | Description |
|---|---|---|
| Bronze | `dags/flakeflow/`, `dags/melhorias/dags/BRONZE_*` | Raw ingestion |
| Silver | `dags/simon/silver/`, `dags/simon/full_silver/`, `dags/melhorias/dags/SILVER_*` | Cleaning/transformation |
| Gold | `dags/simon/gold/`, `dags/simon/full_gold/` | Business aggregations |

`full_*` = truncate+reload; others = incremental/merge.

## DAG Folder Convention

```
dags/<domain>/dags/<DAG_NAME>/
    <DAG_NAME>.py
    sql_files/
        *.sql
```

Load SQL via `read_sql_file(filename, __file__)`. SQL must always live in `sql_files/` co-located with the DAG file.

## DAG Patterns

**Incremental** — `@dag` decorator + `dag_factory()` called at module level:

```python
@dag(dag_id="...", default_args=default_args, ...)
def dag_factory():
    ...

dag_factory()
```

**Full-reload** (`full_silver/`, `full_gold/`) — `with DAG(...)` context manager. Do not mix styles.

Standard `default_args`: build them with `default_dag_args(owner=..., start_date=...)` from `global_modules/dag_defaults.py` (pass keyword overrides for exceptions) instead of writing the dict by hand. DAGs that still hand-write `default_args` (no retries: `full_silver/*` — manual, heavy extraction on the 2008 R2 sources — and manual/admin DAGs) are deliberate exceptions, not a pattern to copy. Policy: `on_failure_callback: notify_teams_on_failure`, `retries=2`, `retry_delay=timedelta(minutes=2)`, `retry_exponential_backoff=True`, `max_retry_delay=timedelta(minutes=30)`, `execution_timeout=timedelta(minutes=45)`. Tasks that can legitimately run longer override `execution_timeout` on the `@task` itself; register them in `EXECUTION_TIMEOUT_OVERRIDES` (`tests/test_dags_default_args.py`). Tasks that extract from SharePoint (Graph API throttling) use `@task(**SHAREPOINT_EXTRACT_RETRY_ARGS)` and are registered in `SHAREPOINT_EXTRACT_TASKS` in the same test. DAGs that still hand-write `default_args` must include `"execution_timeout": DEFAULT_EXECUTION_TIMEOUT`; the test checks every task in the DagBag.

**Scheduling**: Gold DAGs use `schedule=[<Dataset>]` triggered by Silver DAG outlets — not cron. New DAGs should use Datasets, not `CustomSqlSensor`.

## Global Modules (`dags/global_modules/`)

`database.py` · `mssql.py` (driver ODBC via Variable `MSSQL_ODBC_DRIVER`; não fixar driver no código) · `utils.py` · `operators.py` · `functions.py` (lê `global_files/global_config.yml`) · `sharepoint/` (Graph API) · `pg_load.py` (`replace_pg_table` / `pg_transaction`: truncate+carga no Postgres numa transação só; usar em vez de `TRUNCATE` via `postgres_execute` solto).

`teams/` é o módulo atual de notificação (Adaptive Cards). `ms_teams.py` é apenas shim de compatibilidade — não usar em código novo.

## ETL Stack

ConnectorX (`cx.read_sql`) extrai SQL para Arrow; DuckDB processa in-process e faz bulk load no Postgres via `ATTACH` + `INSERT INTO pg.*` (não usar cursor linha a linha). SQLAlchemy/psycopg2 ficam para merge procedures e operações diretas no Postgres.

## Further Reference

- [`docs/configuration.md`](docs/configuration.md) — Airflow variables, connections, establishment codes
- [`docs/dag-patterns.md`](docs/dag-patterns.md) — Idempotency sentinels, legacy `CustomSqlSensor`

## Agent skills

### Issue tracker

Issues live in GitLab Issues (self-hosted, `glab` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/`; dbt melhorias keeps scoped ADRs in `dags/melhorias/dbt/docs/adr/`. See `docs/agents/domain.md`.
