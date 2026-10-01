# ADR = Architecture Decision Record.

# 0005 — Materializar o caminho quente de ganhos como tabela columnstore

- Status: aceito
- Data: 2026-06-18
- Supersede parcialmente: [ADR 0001](0001-dbt-views-only-sql-server.md) (views-only)
- Complementado por: [ADR 0009](0009-compilacao-int-ganhos-calc.md) (`int_ganhos_calc`
  também como tabela, volume histórico pivotado)
- Baseado em: [cost-analysis-mel-storage.md](../cost-analysis-mel-storage.md),
  [performance-threshold.md](../performance-threshold.md)

## Contexto

ADR 0001 fixou todos os modelos como VIEW, justificado por (a) teto de 10 GB no
SQL Server e (b) consumo via Power BI import. A `performance-threshold.md` mediu
que o custo NÃO escala pela linha do fato e sim pela **recomputação da subárvore
de views**: `mel_int_ganhos_long` (unpivot 4×, 339k linhas) é recomputado por
`fct_ganhos` E por `int_melhorias_realizado` (→ `fct_aderencia`) a cada refresh.
`fct_ganhos` leva ~5s e `fct_aderencia` ~3s no `SELECT *` por causa disso.

A análise de custo (cost-analysis-mel-storage.md, 2026-06-18) provou que storage
não é o bloqueio: materializar o caminho quente com clustered columnstore custa
~10-20 MB e cresce ~6-8 MB/ano — desprezível frente aos 10 GB.

## Decisão

1. Materializar como **`table` com clustered columnstore** (default
   `as_columnstore=true` do dbt-sqlserver, suportado no 2019 Standard) os modelos
   do caminho quente:
   - `int_ganhos_long` (corta recomputação dupla + unpivot)
   - `fct_ganhos`, `fct_meta`, `fct_aderencia` (extração instantânea no refresh)
2. **Tabela, não incremental**: `mel_ganhos` é full-reload do SharePoint com
   edições retroativas (`Modified`, `volume_foi_editado`). Incremental append
   silenciaria edições antigas; o rebuild completo sobre columnstore é sub-segundo
   no volume atual.
3. Demais modelos (staging, dims, intermediate restante,
   `fct_melhorias_em_andamento`) permanecem **VIEW** — rápidos e sem ganho em
   materializar (YAGNI; dims minúsculas, fct de 40ms).
4. Configuração por modelo (`{{ config(materialized='table') }}`), não por pasta:
   o default do projeto segue `view` (ADR 0001), com exceção pontual e explícita.

## Consequências

- Storage extra ~10-20 MB hoje, ~6-8 MB/ano; folga enorme nos 10 GB.
- Refresh do Power BI deixa de recomputar a subárvore de ganhos; `fct_ganhos` /
  `fct_aderencia` viram extração direta de tabela comprimida.
- Ordem de build: `int_ganhos_long` materializa antes dos `fct_*` que o leem (dbt
  resolve pelo grafo de `ref()`).
- Rebuild a cada `dbt build` (full refresh). Se o volume de `mel_ganhos` crescer
  muito além de ~300k (ver threshold), reavaliar incremental por bimestre com
  watermark por `Modified` para cobrir edições retroativas.
- ADR 0001 segue válido para o resto: redundância mínima, default view, bronze
  imutável como source.

## Alternativas consideradas

- **Incremental por bimestre**: economiza rebuild, mas arrisca staleness com
  edições retroativas e adiciona complexidade sem ganho de tempo relevante no
  volume atual. Rejeitado por ora.
- **Manter tudo view (ADR 0001 puro)**: deixaria `fct_ganhos`/`fct_aderencia`
  lentos no refresh sem necessidade, já que storage não é restrição.
- **Materializar tudo como tabela**: ~180 MB; ruído em dims minúsculas, contra
  YAGNI. Sem ganho frente ao caminho quente.
