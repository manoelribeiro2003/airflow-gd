# Migração Qlik → SQL + dbt (Melhorias)

Migrar a regra de negócio do indicador de Melhorias (Aderência / Ganhos) do Qlik
para dbt sobre o SQL Server `dbengenharia.dbo`. Power BI (import) substitui o Qlik.

Fontes de referência:
- `./qlik/` — scripts Qlik (regra de negócio original).
- `./ddl/` — DDL das tabelas SQL Server.
- `CONTEXT.md` — glossário do domínio.
- `adr/` — decisões de arquitetura.

## Abordagem

dbt direto (sem etapa de `CREATE VIEW` solto antes). Itera o `SELECT` no
SSMS/DBeaver pra validar vs Qlik, mas commita já como model dbt. Tudo materializado
como VIEW (ver `adr/0001`).

## Decisões fechadas (grilling 2026-06-02)

| Tema | Decisão | Ref |
|---|---|---|
| Conexão | `ENG_DATABASE_URL` (SQL Server) → DAG `make_url` → env vars → `profiles.yml` `env_var()` | adr/0002 |
| Escopo 1ª entrega | tudo de uma vez: 3 fatos + dims + aux | — |
| Aux | seeds (`mel_gerente_remap`, `mel_gerente_area`, `mel_categoria_melhorias`, `mel_bimestre`) + sources populadas via planilha+VBA (`mel_meta_aderencia`, `mel_carga_horaria`, `mel_custo_funcionario`) — sem DAG de ingestão | CONTEXT |
| Remap gerente | seed com `valido_ate` + join janela de data (não CASE no SQL) | — |
| Data mestra | `dt_fap` (aprovacao deriva de `dt_aprovacao_eng`; ganhos usa `dt_fap` nativo de `mel_ganhos`) | adr/0003 |
| Tabela central | `mel_meta_aderencia` (grão `bimestre, crachá`); realizado = melhorias via ganhos | — |
| Melhoria | quantidade: `numero_fap` com `ganho_fap >= 0` E `replicacao = 'Não'`; `ganho_total` soma todos os FAPs (sem filtro) | — |
| Ganho R$ | TC/Aglutinação calculado (`hrs/ch*custo`); Consumo/Troca somados; demais = `ganho_previsto` | qlik |
| Bimestre | `'mes1-mes2/ano'` (ex. `jan-fev/2026`) via seed `mel_bimestre` | — |
| Collation | `mel_ganhos` Latin1 × planilha/seeds UTF8: joins de string com `collate database_default` | adr/0003 |
| Em andamento | fato separado `fct_melhorias_em_andamento`; fatos principais só aprovadas | adr/0003 |
| Grão ganhos | long/unpivot (FAP × mês 1..4) | adr/0003 |
| Local projeto | `dags/melhorias/dbt/` + `.airflowignore` | — |
| `dim_calendario` | date spine `min(dt_fap)`..`max(dt_fap)`, deriva bimestre | adr/0003 |

## Inventário de models

```
staging/   (view 1:1, limpeza sobre source/seed)
  stg_mel_aprovacao        # + dt_fap derivada (COALESCE dt_aprovacao_eng)
  stg_mel_ganhos
  stg_meta_aderencia
  stg_carga_horaria
  stg_custo_funcionario

intermediate/   (regra de negócio)
  int_gerente_remap        # remap (seed + janela data) + área
  int_ganhos_calc          # componentes wide: hrs ganhas, consumo, troca MP (dt_fap nativo de mel_ganhos)
  int_ganhos_long          # unpivot 1..4 + ganho_reais por tipo (R$ trabalhista/consumo/troca/previsto)
  int_melhorias_realizado  # realizado por (bimestre, crachá): melhoria = ganho_reais>0 e replicacao='Não'

marts/   (gold, VIEW, Power BI import)
  dim_calendario
  dim_gerente
  dim_idealizador          # grão (bimestre, crachá)
  dim_tipo_melhoria
  fct_ganhos               # long: FAP × mês 1..4
  fct_aderencia            # meta × realizado (roster completo)
  fct_melhorias_em_andamento

seeds/   (tabelas com prefixo mel_)
  mel_gerente_remap.csv        # origem, destino, valido_ate
  mel_gerente_area.csv         # gerente, area
  mel_categoria_melhorias.csv  # tipo, categoria
  mel_bimestre.csv             # mes, bimestre
```

## Orquestração

Uma DAG dispara `dbt seed` + `dbt build` via BashOperator, acionada pelo Dataset
bronze, emitindo o Dataset gold (ver `adr/0001`). Aposenta a DAG
`SILVER_MELHORIAS_DATA_FAP` (a derivação `dt_fap` migra pra staging/intermediate).

## Pendências de implementação

- `gerentes` e `categoria_das_melhorias` viram seed (não precisam DDL).
- `mel_meta_aderencia`, `mel_carga_horaria`, `mel_custo_funcionario`: populadas
  pelo negócio via planilha + VBA direto no SQL Server. Não há DAG de ingestão; o
  dbt depende delas existirem antes do `dbt build`.
- Reconciliar `ganho em reais` calculado vs `[R$ Mês TC]` da planilha (Qlik guardava ambos).
- Testes dbt mínimos (`unique`/`not_null`/`accepted_values`) já no build verde; falta
  `relationships` fato→dim.
