# ADR = Architecture Decision Record.

# 0002 — Conexão dbt via ENG_DATABASE_URL (Airflow Variable → env_var)

- Status: aceito
- Data: 2026-06-02

## Contexto

O `dbt-sqlserver` lê `profiles.yml`, que não enxerga `Variable.get()` do Airflow.
A credencial do SQL Server `dbengenharia` já existe como a Airflow Variable
`ENG_DATABASE_URL` (URL SQLAlchemy `mssql+pyodbc://...`, usada por `get_eng_conn()`
em `global_modules/database.py`). Não queremos uma segunda credencial.

Nota: a doc legada (`README.md`, `docs/configuration.md`) rotula `ENG_DATABASE_URL`
como "PostgreSQL Engenharia" — está incorreta. O kwarg `fast_executemany` em
`create_engine` é exclusivo `mssql+pyodbc`, confirmando SQL Server.

## Decisão

A DAG de orquestração lê `Variable.get("ENG_DATABASE_URL")`, faz `make_url()`
(SQLAlchemy) pra quebrar em componentes e injeta como env vars no `env=` do
BashOperator que roda `dbt build`:

```
DBT_HOST, DBT_DB, DBT_USER, DBT_PWD  (+ driver/porta conforme a URL)
```

O `profiles.yml` consome via `{{ env_var('DBT_HOST') }}` etc. Fonte de verdade
única: a Variable que já existe.

## Consequências

- Zero credencial nova; sem drift entre dbt e os módulos SQLAlchemy.
- A senha trafega como env var do processo `dbt` no worker (não logar; não commitar).
- Se a URL mudar de formato (ex.: parâmetros de driver), o parsing na DAG precisa
  acompanhar.

## Alternativas consideradas

- **Variables/secrets dedicadas pro dbt** (host/db/user/pass separados): profile mais
  simples, mas duplica credencial e gera drift.
- **`connection_string` pyodbc inteira via env_var**: o formato pyodbc difere da URL
  SQLAlchemy → precisaria converter de qualquer modo.
