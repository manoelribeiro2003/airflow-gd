# ADR = Architecture Decision Record.

# 0001 — dbt views-only sobre SQL Server (dbo), Power BI em import

- Status: aceito
- Data: 2026-06-01

## Contexto

Migração das regras de negócio de Melhorias do Qlik para SQL + dbt. As tabelas
bronze (`mel_aprovacao`, `mel_ganhos`) já vivem no SQL Server `dbengenharia.dbo`,
ingeridas por DAGs Airflow a partir do SharePoint. O consumidor final será um novo
dashboard em **Power BI** (Qlik será aposentado).

Restrição dura: o banco SQL Server tem apenas **10GB** de espaço total.

## Decisão

1. **Adapter**: `dbt-sqlserver`, mirando o próprio `dbengenharia` — zero
   movimentação de dados; a regra fica colada na fonte.
2. **Tudo em `dbo`**: sem schemas `silver`/`gold` dedicados; reusar/ajustar os
   `mel_*`. Redundância mínima por causa do limite de 10GB.
3. **Materialização = VIEW** para todos os models (staging, intermediate, gold).
   Nenhuma cópia física de dado no banco. O Power BI em **modo import** copia os
   dados para o `.pbix` no refresh, então não precisa de tabela física no SQL
   Server.
4. **Bronze imutável**: dbt trata `mel_*` como `sources` e nunca escreve neles.
   Derivações antes feitas via UPDATE in-place (ex.: `dt_fap`) viram colunas
   derivadas em views silver.
5. **Orquestração**: uma DAG roda `dbt build` via BashOperator, disparada pelo
   Dataset bronze, emitindo o Dataset gold.

## Consequências

- Storage extra no SQL Server ≈ 0; cabe no orçamento de 10GB.
- Custo de query empurrado para o refresh do Power BI (import), não para o banco.
- Se algum model-view ficar lento no refresh, materializar aquele model específico
  como tabela é uma exceção pontual (não o padrão). Threshold medido e gatilho de
  materialização em [performance-threshold.md](../performance-threshold.md): o
  gargalo é `int_ganhos_long` (unpivot 4×, recomputado por cada consumidor); começar
  a agir perto de ~250-300k linhas em `mel_ganhos` (~3× o atual de 102k).
- DirectQuery não é suportado de forma performática (views sem índice próprio); a
  decisão pressupõe import. Mudar para DirectQuery exigiria reavaliar (tabelas +
  índices vs limite de 10GB).
- A DAG `SILVER_MELHORIAS_DATA_FAP` (update_fap in-place) será aposentada.

## Alternativas consideradas

- **Postgres / DuckDB**: exigiria pipeline de cópia SQL Server→destino e mover o
  consumo do dashboard; mais atrito, sem ganho dado que a fonte já é SQL Server.
- **Gold como tabelas**: melhor para DirectQuery/performance no banco, mas duplica
  dados — inviável sob 10GB.
- **Schemas silver/gold dedicados**: mais limpo conceitualmente, porém o usuário
  priorizou redundância/ruído mínimos em `dbo`.
