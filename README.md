# Airflow Data Pipeline — SiMOn

Pipeline de dados da equipe de dados responsável por consolidar indicadores de qualidade, disponibilidade e performance das fábricas. Alimenta o **SiMOn** (Sistema de Monitoramento Online) e outros sistemas a partir de múltiplas fontes — Elipse, Flakeflow e SharePoint — entregando os dados tratados nas camadas Silver e Gold.

## Visão Geral da Arquitetura

```
Elipse (SOB / FOR / CRA)  ─┐
Flakeflow                  ├──► Bronze / Silver ──► Gold ──► SiMOn
SharePoint                 ┘
```

O pipeline segue a arquitetura medallion:

| Camada          | Domínio             | Descrição                                                                                                         |
| --------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Bronze**      | `flakeflow`         | Ingestão bruta do Flakeflow (área, eventos, SKU, produtos relacionados)                                           |
| **Silver**      | `simon/silver`      | Limpeza e transformação incremental dos dados Elipse (ciclos, qualidade, disponibilidade, performance, dimensões) |
| **Silver Full** | `simon/full_silver` | Reload completo das tabelas Silver                                                                                |
| **Gold**        | `simon/gold`        | Modelos dimensionais e fatos agregados para o SiMOn                                                               |
| **Gold Full**   | `simon/full_gold`   | Reload completo das tabelas Gold                                                                                  |

**Estabelecimentos Elipse**

| Chave | Código | Localidade |
| ----- | ------ | ---------- |
| `sob` | 20     | Sobral     |
| `for` | 21     | Fortaleza  |
| `cra` | 40     | Crato      |

## Stack Tecnológica

| Componente             | Tecnologia                             |
| ---------------------- | -------------------------------------- |
| Orquestração           | Apache Airflow 2.10.5 (CeleryExecutor) |
| Broker                 | Redis 7.2                              |
| Metadata DB            | PostgreSQL 13                          |
| Extração               | ConnectorX (Arrow)                     |
| Processamento          | DuckDB, Polars, Pandas                 |
| Containerização        | Docker / Docker Compose                |
| Gerenciador de pacotes | uv                                     |
| Linting Python         | Ruff                                   |
| Linting SQL            | SQLFluff                               |

## Pré-requisitos

- Docker e Docker Compose
- [uv](https://docs.astral.sh/uv/) instalado

## Instalação e Execução

**1. Copiar e preencher as variáveis de ambiente:**

```bash
cp .env.example .env
```

Edite o `.env` ajustando ao menos:

| Variável | Descrição |
|---|---|
| `AIRFLOW_UID` | UID do usuário Linux (`id -u`); evita arquivos criados como root |
| `DRIVER_PATH` | Caminho do volume onde os parquets de extração são gravados |
| `DOCKER_REGISTRY` | Registry privado para push/pull da imagem (ex: `10.2.24.20:5000/`) |
| `SHAREPOINT_USERNAME` | Usuário de serviço para acesso ao SharePoint |
| `SHAREPOINT_USER_PASSWORD` | Senha do usuário de serviço SharePoint |

**2. Instalar dependências de desenvolvimento:**

```bash
uv sync --group dev
```

**3. Subir o ambiente:**

```bash
uv run task docker   # detached
uv run task dw       # com watch — rebuild automático em mudanças de arquivo
```

O Airflow ficará disponível em `http://localhost:8080` (usuário/senha padrão: `airflow/airflow`).

## Comandos de Desenvolvimento

```bash
uv run task lint         # Verificação de estilo Python (ruff check)
uv run task format       # Correção automática + formatação Python (ruff)
uv run task lint-sql     # Verificação de estilo SQL (sqlfluff lint dags/)
uv run task format-sql   # Formatação SQL (sqlfluff format dags/)
uv run task test         # Testes com cobertura (pytest); roda lint antes; gera htmlcov/
uv run task build        # Build da imagem Docker
uv run task push         # Build + push para o registry
```

**Rodar um único arquivo de teste:**

```bash
uv run pytest -s -x -vv path/to/test_file.py
```

## Estrutura do Projeto

```
dags/
├── global_modules/         # Utilitários compartilhados entre todas as DAGs
│   ├── database.py         # Factories de conexão (Elipse, ConnectorX, DuckDB, Postgres)
│   ├── utils.py            # read_sql_file(), get_parquet_file(), get_sentinel_file()
│   ├── operators.py        # CustomSqlSensor
│   ├── ms_teams.py         # Callback de falha via webhook Teams
│   ├── sqlserver_hook.py   # Hook pyodbc para SQL Server
│   └── sharepoint/         # Integração com listas SharePoint
├── global_files/
│   └── sql_files/
│       └── wait_dependencies.sql   # SQL para sensor de dependências entre DAGs
├── simon/                  # DAGs do domínio SiMOn (OEE)
│   ├── silver/             # Carga incremental Silver
│   ├── full_silver/        # Reload completo Silver
│   ├── gold/               # Carga incremental Gold
│   └── full_gold/          # Reload completo Gold
├── flakeflow/              # DAGs Bronze do Flakeflow
├── melhorias/              # DAGs do domínio de melhorias
└── airflow/                # DAGs de manutenção do próprio Airflow
```

O domínio **melhorias** usa dbt (Qlik → SQL + dbt) sobre `dbengenharia`. Detalhes,
modelos, decisões (ADRs) e análise de custo/storage em
[`dags/melhorias/dbt/README.md`](dags/melhorias/dbt/README.md).

Cada DAG reside em sua própria pasta com a estrutura:

```
dags/<domínio>/dags/<NOME_DA_DAG>/
    <NOME_DA_DAG>.py
    sql_files/
        extract_query.sql
        merge_query.sql
```

## Variáveis do Airflow

As seguintes variáveis precisam estar cadastradas no Airflow antes de executar as DAGs:

| Variável                         | Descrição                                            |
| -------------------------------- | ---------------------------------------------------- |
| `CX_ELIPSE_SOB`                  | Connection string ConnectorX — Elipse Sobral         |
| `CX_ELIPSE_FOR`                  | Connection string ConnectorX — Elipse Fortaleza      |
| `CX_ELIPSE_CRA`                  | Connection string ConnectorX — Elipse Crato          |
| `CX_ELIPSE_PG`                   | Connection string ConnectorX — PostgreSQL Engenharia |
| `CX_FLAKEFLOW_CONN`              | Connection string ConnectorX — Flakeflow             |
| `DDB_PG_CONN`                    | String de attach DuckDB → PostgreSQL Engenharia      |
| `DDB_PG_FLAKEFLOW_CONN`          | String de attach DuckDB → PostgreSQL Flakeflow       |
| `ENG_DATABASE_URL`               | SQLAlchemy URL — SQL Server Engenharia (dbengenharia) |
| `MSSQL_ODBC_DRIVER`              | Driver ODBC do SQL Server (opcional; padrão `ODBC Driver 17 for SQL Server`) |
| `WEBHOOK_TEAMS`                  | URL do webhook para notificações de falha no Teams   |
| `SILVER_F_CICLOS_DAYS_TO_SEARCH` | Janela de busca em dias para o pipeline de ciclos    |

## Autores

- [Yan Arcanjo](https://www.linkedin.com/in/yanarcanjo21/)
- [Antonio Albuquerque](https://www.linkedin.com/in/antonio-albuquerque-loiola/)
