# Configuration Reference

## Establishment Codes

Elipse source data comes from three establishments:

| Key | Code | Location | Airflow conn var |
|---|---|---|---|
| `sob` | 20 | Sobral | `elipse_sob` / `CX_ELIPSE_SOB` |
| `for` | 21 | Fortaleza | `elipse_for` / `CX_ELIPSE_FOR` |
| `cra` | 40 | Crato | `elipse_cra` / `CX_ELIPSE_CRA` |

## Airflow Connections

| Connection | Used by |
|---|---|
| `postgres_eng_server` | All Gold DAGs (`SQLExecuteQueryOperator`) |
| `elipse_sob`, `elipse_for`, `elipse_cra` | SQL Server extraction in `full_silver` DAGs (`get_mssql_url`) |

## Airflow Variables

| Variable | Used for |
|---|---|
| `CX_ELIPSE_SOB`, `CX_ELIPSE_FOR`, `CX_ELIPSE_CRA` | ConnectorX connection strings for Elipse establishments |
| `CX_ELIPSE_PG` | ConnectorX connection to Postgres |
| `CX_FLAKEFLOW_CONN` | ConnectorX connection to Flakeflow source |
| `DDB_PG_CONN` | DuckDB ATTACH string for engineering Postgres |
| `DDB_PG_FLAKEFLOW_CONN` | DuckDB ATTACH string for Flakeflow Postgres |
| `ENG_DATABASE_URL` | SQLAlchemy URL for engineering SQL Server (dbengenharia) |
| `MSSQL_ODBC_DRIVER` | ODBC driver for every `mssql+pyodbc` connection, the custom `SqlServerHook` and dbt (default `ODBC Driver 17 for SQL Server`; overrides the `driver` in `ENG_DATABASE_URL`/`elipse_*`). Use `global_modules.mssql`. |
| `WEBHOOK_TEAMS` | MS Teams webhook URL for failure alerts |
| `SILVER_F_CICLOS_DAYS_TO_SEARCH` | Integer lookback window for ciclos pipeline |
| `SHAREPOINT_SITE_URL` | SharePoint site URL (`https://contoso.sharepoint.com/sites/nome`) |
| `SHAREPOINT_CLIENT_ID` | Azure AD App Registration client ID |
| `SHAREPOINT_CLIENT_SECRET` | Azure AD App Registration client secret |
| `SHAREPOINT_LIST_NAME` | SharePoint list name (default; can be overridden per call) |
| `SHAREPOINT_TENANT_ID` | Azure AD tenant ID — required for `fetch_sharepoint_items_with_graph_api` |
