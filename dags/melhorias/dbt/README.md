# dbt — Melhorias

Migração da regra de negócio de Melhorias (Qlik → SQL + dbt) sobre SQL Server
`dbengenharia.dbo`. Plano e decisões em [`docs/`](docs/) (IDEIA, CONTEXT, ADRs).
Linhagem completa (sources → marts, com diagramas) em [`docs/lineage.md`](docs/lineage.md).

## Documentação

| Doc | Conteúdo |
|---|---|
| [`docs/lineage.md`](docs/lineage.md) | Linhagem canônica (sources → marts) com diagramas |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) / [`docs/IDEIA.md`](docs/IDEIA.md) | Contexto e plano da migração |
| [`docs/performance-threshold.md`](docs/performance-threshold.md) | Medição de performance das views; gargalo `int_ganhos_long`; threshold para materializar |
| [`docs/reconciliacao-qlik-2021-2025.md`](docs/reconciliacao-qlik-2021-2025.md) | Reconciliação dos ganhos 2021-2025 contra as planilhas do Qlik, gaps explicados por FAP |
| [`docs/cost-analysis-mel-storage.md`](docs/cost-analysis-mel-storage.md) | Custo bytes/row das `mel_`, projeção de crescimento, espaço atual do banco e resultado pós-materialização |
| [`docs/adr/0001-dbt-views-only-sql-server.md`](docs/adr/0001-dbt-views-only-sql-server.md) | Views-only sobre SQL Server, Power BI import, teto 10 GB |
| [`docs/adr/0002-conexao-eng-database-url-via-env-var.md`](docs/adr/0002-conexao-eng-database-url-via-env-var.md) | Credencial via `ENG_DATABASE_URL` → env vars `DBT_*` |
| [`docs/adr/0003-contrato-gold-ganhos-long-dt-fap-aprovadas.md`](docs/adr/0003-contrato-gold-ganhos-long-dt-fap-aprovadas.md) | Contrato gold ganhos long (dt_fap, aprovadas) |
| [`docs/adr/0004-seed-manual-sql-server.md`](docs/adr/0004-seed-manual-sql-server.md) | Seeds carregados manualmente no SQL Server |
| [`docs/adr/0005-materializar-caminho-quente-ganhos.md`](docs/adr/0005-materializar-caminho-quente-ganhos.md) | Materializa caminho quente de ganhos como tabela columnstore (supersede parcial do ADR 0001) |
| [`docs/adr/0006-carga-horaria-macro-setor-corte-qlik.md`](docs/adr/0006-carga-horaria-macro-setor-corte-qlik.md) | Carga horária por macro setor (planilha Qlik) e corte do histórico `volume_hist_ate` |
| [`docs/adr/0007-volume-real-historico-planilhas-qlik.md`](docs/adr/0007-volume-real-historico-planilhas-qlik.md) | Volume real 2021-2025 das planilhas do Qlik (`mel_volume_real_hist`) antes do corte `volume_hist_ate` |
| [`docs/adr/0008-ganhos-historicos-faps-ausentes-planilhas-qlik.md`](docs/adr/0008-ganhos-historicos-faps-ausentes-planilhas-qlik.md) | FAPs aprovadas sem linha em `mel_ganhos` entram pelas planilhas do Qlik (`mel_ganhos_hist`, `union all` em `stg_mel_ganhos`) |
| [`docs/adr/0009-compilacao-int-ganhos-calc.md`](docs/adr/0009-compilacao-int-ganhos-calc.md) | Volume histórico pivotado antes do join e `int_ganhos_calc` como tabela: compilação de 441 s para 0,7 s |
| [`docs/adr/0010-troca-mp-tc-aglutinacao-ting.md`](docs/adr/0010-troca-mp-tc-aglutinacao-ting.md) | TC/Aglutinação de setor Ting% vale só as horas (planilha); `troca_mp` só para Consumo e Troca MP |
| [`docs/adr/0011-ajustes-cadastro-e-faps-2021-fora-da-carga.md`](docs/adr/0011-ajustes-cadastro-e-faps-2021-fora-da-carga.md) | Ganho corrigido pela planilha (seed `mel_ganhos_ajuste`) e carga das FAPs aprovadas de 2021 que ficaram fora de `mel_aprovacao` |
| [`docs/adr/0012-macro-setor-por-mapa-e-zero-do-numero-fap.md`](docs/adr/0012-macro-setor-por-mapa-e-zero-do-numero-fap.md) | `macro_setor` nulo preenchido pelo mapa de setor (seed `mel_macro_setor`) e zero à esquerda do número da FAP em `mel_volume_real_hist` |
| [`docs/adr/0013-ganho-da-planilha-para-cadastro-divergente.md`](docs/adr/0013-ganho-da-planilha-para-cadastro-divergente.md) | FAP de TC e MP com cadastro incompleto ou divergente usa as linhas da planilha (seed `mel_ganhos_fonte_planilha`); linha sem código fica com `SEM_CODIGO` |

## Rodar

A credencial vem da Airflow Variable `ENG_DATABASE_URL` injetada como env vars
(ADR 0002). Localmente, exportar:

```bash
export DBT_HOST=... DBT_DB=dbengenharia DBT_USER=... DBT_PWD=... DBT_PORT=1433
dbt deps --profiles-dir .
dbt build --exclude resource_type:seed --indirect-selection cautious --profiles-dir .
```

O `dbt seed` foi descontinuado: as tabelas `mel_*` auxiliares são carregadas
manualmente no SQL Server (DBeaver/SQL), não via dbt. Por isso o build usa
`--exclude resource_type:seed`. Ver ADR 0004. O `--indirect-selection cautious` mantém
no build os testes que cruzam um seed com outra fonte; sem ele o `--exclude` os tira
junto com os seeds (ADR 0013).

Padrão de materialização: **VIEW** no schema `dbo` (limite de 10 GB, import do Power
BI — ADR 0001). **Exceção (ADR 0005)**: o caminho quente de ganhos
(`int_ganhos_calc` (ADR 0009), `int_ganhos_long`, `fct_ganhos`, `fct_aderencia`) é **table com
clustered columnstore** — corta a recomputação repetida de `int_ganhos_long`
(`fct_aderencia` 32× mais rápido) e custa ~5 MB. Ver
[`docs/cost-analysis-mel-storage.md`](docs/cost-analysis-mel-storage.md) e
[`docs/performance-threshold.md`](docs/performance-threshold.md).

## Estrutura

- `models/staging/` — limpeza 1:1 sobre sources e tabelas auxiliares.
- `models/intermediate/` — regra de negócio (remap de gerente, cálculo de ganhos,
  unpivot/conversão R$, realizado, date spine).
- `models/marts/` — gold (dims + fatos), consumido pelo Power BI (import).
- `macros/generate_alias_name.sql` — prefixa toda relação criada pelo dbt com
  `mel_` (regra do projeto). No banco: `mel_stg_*`, `mel_int_*`, `mel_dim_*`,
  `mel_fct_*`. Os `ref()` continuam usando o node name (sem prefixo).
- `seeds/` — CSVs de mapeamento estático (`mel_bimestre`, `mel_categoria_melhorias`,
  `mel_gerente_remap`, `mel_gerente_area`, `mel_ganhos_ajuste`, `mel_macro_setor`,
  `mel_ganhos_fonte_planilha`), mantidos só como referência/contrato de
  schema. Não são mais carregados via `dbt seed`: as tabelas `dbo.mel_*` são populadas
  manualmente no SQL Server. Ver ADR 0004.

## Modelos

Tabela canônica (com upstream imediato e descrição por modelo) em
[`docs/lineage.md`](docs/lineage.md). Resumo das camadas:

| Camada | Modelos |
|---|---|
| staging | `stg_mel_aprovacao`, `stg_mel_ganhos`, `stg_mel_volume_real`, `stg_mel_volume_real_hist`, `stg_meta_aderencia`, `stg_carga_horaria`, `stg_carga_horaria_macro`, `stg_custo_funcionario` |
| intermediate | `int_ganhos_calc`, `int_ganhos_long`, `int_melhorias_realizado`, `int_gerente_remap`, `int_calendario_spine` |
| marts (dims) | `dim_calendario`, `dim_gerente`, `dim_idealizador`, `dim_tipo_melhoria` |
| marts (fatos) | `fct_aderencia`, `fct_ganhos`, `fct_melhoria`, `fct_melhorias_em_andamento` |

`int_ganhos_calc`, `int_ganhos_long`, `fct_ganhos`, `fct_aderencia` e `fct_melhoria` são
materializados como **table (clustered columnstore)**; os demais como **view**. Ver ADRs
0005 e 0009.

`fct_melhoria` é o fato resumo no grão **1 linha por FAP**: junta atributos de aprovação
(`status`, `tipo_produto`, `tipo_melhoria`) com o ganho agregado por FAP (`ganho_reais` R$,
`replicacao`, `origem_melhoria`). Roster completo (todas as FAPs, todos os status); ganho
entra por left join. Expõe `sk_idealizador` (relação com `dim_idealizador`).

`stg_meta_aderencia` (sobre `mel_meta_aderencia`) é a tabela **central**, grão
`(bimestre, crachá)`: alimenta a aderência/roster (`fct_aderencia`, roster completo),
`dim_idealizador` e o remap de gerente (`int_gerente_remap` → `dim_gerente`).

## Aderência (meta × realizado)

`fct_aderencia` cruza meta x realizado no grão `(bimestre, crachá)` e responde, por
idealizador/bimestre: quantas melhorias fez, atingiu a meta, ganhou quanto.

- **Realizado** (`int_melhorias_realizado`): `qtde_melhorias` conta FAPs distintas com
  `ganho_fap >= 0` E `replicacao = 'Não'` (melhoria = original, não replicação). Já o
  `ganho_total` soma **todos** os ganhos por FAP do idealizador/bimestre, independente
  de replicacao/sinal (não usa o filtro da contagem).
- **Meta**: roster elegível vindo de `stg_meta_aderencia` (meta fixa de 1 por elegível).

Bimestre canônico em todo o modelo: `'mes1-mes2/ano'` (ex. `jan-fev/2026`), derivado
de `dt_fap` (ganhos/aprovação) ou `inicio_bimestre` (meta) via seed `mel_bimestre`.

**Chave de relação Power BI (`sk_idealizador`).** O import só relaciona por chave de 1
coluna, mas o grão do idealizador é composto `(bimestre, crachá)`. `dim_idealizador`
expõe `sk_idealizador = concat(bimestre, '|', crachá)` como PK da dimensão-ponte, e
`fct_aderencia`/`fct_ganhos` expõem a mesma chave como FK (relação fato → dim, não
fato-a-fato). `collate database_default` no concat resolve o conflito de collation.
`fct_melhorias_em_andamento` não recebe a chave (sem bimestre, ADR 0003).

## Ganhos (cálculo R$)

`int_ganhos_calc` calcula os ganhos ainda WIDE (meses 1..4 em colunas) seguindo a regra
Qlik. O volume real do mês vem de `stg_mel_volume_real_hist` (planilhas do Qlik) quando
a competência é anterior ao corte `volume_hist_ate`, e de `stg_mel_volume_real` depois
(ADR 0007). `int_ganhos_long` faz o unpivot 1..4 e a conversão por tipo, gerando uma linha por
`(FAP, mês de competência)` consumida por `fct_ganhos`:

- **TC/Aglutinação**: R$ trabalhista (`hrs_ganhas / ch_mensal * custo`, competência = mês
  de `dt_fap`). `ch_mensal` e `custo` são resolvidos em `int_ganhos_calc`: carga por
  macro setor (`stg_carga_horaria_macro`) antes do corte `volume_hist_ate`; depois, por
  setor (`stg_carga_horaria`) com fallback macro quando nula ou 0 (ADR 0006).
- **Consumo/Troca MP**: já em R$, somados.
- **Demais tipos**: `ganho_previsto` no mês 1.

## Collation

`mel_ganhos` (ingerido por DAG) é `Latin1_General_CI_AS`; tabelas de planilha/VBA
(`mel_carga_horaria`, `mel_custo_funcionario`) e as tabelas `mel_*` auxiliares são
`Latin1_General_100_CI_AS_SC_UTF8`. Os joins de string entre as duas origens em
`int_ganhos_calc` usam `collate database_default` pra não estourar conflito. Ver ADR 0003.

## Pendências (TODO nos models)

- `mel_gerente_area`: popular a tabela no SQL Server com a planilha `gerentes`
  (CSV `seeds/mel_gerente_area.csv` serve de referência do schema).
