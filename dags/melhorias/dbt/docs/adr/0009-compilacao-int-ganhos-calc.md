# 0009 — Volume histórico pivotado e `int_ganhos_calc` como tabela

- Status: aceito
- Data: 2026-09-28
- Issue: #22
- Complementa: [ADR 0005](0005-materializar-caminho-quente-ganhos.md) (caminho quente
  de ganhos como tabela)

## Contexto

Depois dos ADRs 0007 e 0008 e do fallback de código arredondado da #21,
`int_ganhos_calc` passou a ter 15 left joins: 4 meses × (`mel_volume_real`, histórico
com código exato, histórico com código arredondado), mais carga, carga macro e custo.
Tudo isso fica sobre o `union all` de `stg_mel_ganhos`. O custo não estava nos dados
(~290 mil linhas), e sim na **compilação**. No plano estimado de
`select * from mel_int_ganhos_calc` (view, com o fix da #21):

- `CompileTime` = 441 s, `CompileCPU` = 207 s, `StatementOptmEarlyAbortReason=TimeOut`;
- custo estimado de 145, ou seja, baixo.

`int_ganhos_long` faz o unpivot com `union all` de 4 selects sobre o calc, então o
otimizador recebe 4 cópias da árvore. Antes da #21, o `int_ganhos_long` levava 751 s
dos 817 s do `dbt build`. Com o fix, ele não terminou em mais de 1h30 e travou o build de
prod: a sessão presa segurava as views de staging, e os builds seguintes esperavam por ela.

O modelo incremental não resolve, porque compilaria a mesma consulta, e o ADR 0005 já o
rejeitou por causa das edições retroativas.

## Decisão

1. **Histórico pivotado antes do join.** `volume_real_hist` em `int_ganhos_calc` agrupa
   `stg_mel_volume_real_hist` por `(numero_fap, cod_prod)` com `volume_1..4`
   (`sum(case when mes_offset = n ...)`). O calc faz 2 joins com ele (código exato e
   `cod_prod_hist_float`) em vez de 8, e mantém `coalesce(exato, arredondado, 0)` por
   mês. A PK `(numero_fap, cod_prod, mes_offset)` garante uma linha por mês; mês sem
   linha dá `null`, como no left join por mês.
2. **`int_ganhos_calc` como `table`** (clustered columnstore, como no ADR 0005). O
   cálculo roda uma vez por build; `int_ganhos_long` (4 leituras) e
   `int_ganhos_previsto` leem a tabela.

Os joins de `mel_volume_real` (4, um por mês, com `mes_ano` relativo a `dt_fap`)
ficaram como estavam: depois do pivot do histórico, a compilação já é desprezível.

## Medição (dbengenharia, 2026-09-28)

| | Antes (fix #21, view) | Depois (pivot) |
|---|---|---|
| Compilação de `int_ganhos_calc` | 441 s (CPU 207 s), timeout | 0,7 s (CPU 0,2 s) |
| Compilação de `int_ganhos_long` (calc inline, 4×) | não terminou | 17 s |
| Execução de `int_ganhos_long` (calc inline, 4×) | não terminou | 240 s |
| Execução de uma leitura do calc (recorte da #21) | < 15 min | 72 s |

Com o calc materializado, o cálculo roda uma vez, e não 4.

Equivalência: o recorte da reconciliação da #21 (offsets 1 e 2, `dt_fap` 2020-12 a
2025, tipos com volume; 98.018 linhas FAP × mês) sai idêntico ao do SQL anterior. A
diferença é 0 em horas, pessoas, R$, carga e custo, e todos os atributos são iguais. O
caminho de `mel_volume_real` (competência a partir de 2026) não mudou.

## Consequências

- Mais uma tabela columnstore: ~290 mil linhas largas (componentes realizado e previsto
  dos meses 1 a 4). Fica na casa de dezenas de MB, longe do teto de 10 GB (ADR 0001).
- Trocar a view pela tabela exige um `dbt build` sem outra sessão lendo
  `mel_int_ganhos_calc` (bloqueio de schema).
- Novo join no calc: antes de acrescentar, medir a compilação com `SET SHOWPLAN_XML ON`
  (`CompileTime`/`CompileCPU` no XML). Uma consulta que leva minutos só para compilar
  trava o build inteiro.
