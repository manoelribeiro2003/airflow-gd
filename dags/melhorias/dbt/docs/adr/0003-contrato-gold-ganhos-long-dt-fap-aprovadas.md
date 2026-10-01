# ADR = Architecture Decision Record.

# 0003 — Contrato gold: ganhos long, dt_fap mestra, só aprovadas

- Status: aceito
- Data: 2026-06-02

## Contexto

O Qlik (`base_melhoria`) é WIDE — o ganho quadrimestral vive em colunas paralelas
(`hrs ganhas 1..4`, `g consumo 1..4`, `ganho troca MP 1..4`, `ganho em reais 1..4`).
A data de calendário no Qlik era espalhada ("Data da FAP" em ganhos, "Data para
Meta" em aderência), e melhorias em andamento eram jogadas no mês atual via
`Today()` pra contar no painel. O consumidor agora é Power BI (import, modo estrela).

## Decisão

1. **`fct_ganhos` long/unpivot** — grão = (FAP × mês de competência 1..4). Uma linha
   por mês, `dt_competencia = dt_fap + offset`. Os `_1.._4` do Qlik viram linhas.
   Liga `dim_calendario` por `dt_competencia`; aditivo no Power BI.
2. **`dt_fap` = data mestra única** — `mel_ganhos` tem `dt_fap` nativo (DDL), usado
   direto; em `mel_aprovacao` deriva de `dt_aprovacao_eng` (`status='Aprovado'`).
   Único link temporal dos fatos com `dim_calendario`. Unifica "Data da FAP" e
   "Data para Meta" do Qlik. (Correção: o bimestre dos ganhos sai de `dt_fap` em
   staging, sem join com aprovacao.)
3. **Só aprovadas contam** — só FAP com `status = 'Aprovado'` em `mel_aprovacao` entra
   em `fct_ganhos`/`fct_aderencia` (filtro em `int_ganhos_long`); `dt_fap` null também
   fica fora. `dt_fap` preenchido não basta: `mel_ganhos.dt_fap` vem cru do SharePoint
   e FAP reprovada/expirada/falha no fluxo/cancelada pode ter data (correção #24).
   Melhorias em andamento vão num fato próprio `fct_melhorias_em_andamento`
   (referenciado por `Criado`, com `status` do fluxo + `ganho_previsto`). KPI
   principal não mistura realizado com pendente; gold não depende de `Today()` e
   reconstrói histórico estável.
4. **Meta central + melhoria via ganhos** — `mel_meta_aderencia` é a tabela central
   (grão `bimestre, crachá`). O realizado de aderência **não** é mais contagem de
   aprovadas: melhoria (quantidade) = `numero_fap` com `ganho_fap >= 0` E
   `replicacao = 'Não'`; `ganho_total` soma todos os FAPs do idealizador/bimestre
   independente de replicacao/sinal (`int_melhorias_realizado`). Bimestre canônico
   `'mes1-mes2/ano'`.

## Consequências

- Diverge do Qlik de propósito: ele inflava o mês corrente com pendentes; aqui não.
- `dim_calendario` = date spine determinístico de `min(dt_fap)` a `max(dt_fap)`.
- A conversão R$ trabalhista (`ganho em reais`) usa `carga_horaria` + `custo_funcionario`
  do mês-base da FAP pros 4 offsets (igual Qlik); calcula em `int_ganhos_long` no
  unpivot. Ganho por tipo: TC/Aglutinação calculado, Consumo/Troca somados, demais
  tipos = `ganho_previsto`.
- **Collation**: `mel_ganhos` (ingerido por DAG) vem `Latin1_General_CI_AS`; as
  tabelas de planilha/VBA (`mel_carga_horaria`, `mel_custo_funcionario`) e os seeds
  vêm `Latin1_General_100_CI_AS_SC_UTF8`. Joins de string entre as duas origens
  (`int_ganhos_long`: `macro_setor`/`filial`) usam `collate database_default` nos dois
  lados pra não estourar "collation conflict". Joins de `cracha_idealizador` são `int`
  (não precisam collate). Some o problema de vez se o default do database for UTF8 e
  `mel_ganhos` for reingerido sob ele.
- Quem comparar dashboard novo vs Qlik vai ver diferença no mês corrente (pendentes).

## Alternativas consideradas

- **`fct_ganhos` wide (1 linha/FAP)**: espelha Qlik/planilha, mas Power BI só linka
  calendário por `dt_fap` base; fatiar por mês de competência exigiria unpivot em DAX.
- **Replicar em andamento no mês atual** (opção B do grilling): mais fiel, mas mistura
  realizado + previsão e amarra o gold à data de execução.
