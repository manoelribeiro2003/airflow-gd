# ADR = Architecture Decision Record.

# 0006 — Carga horária por macro setor e corte do histórico Qlik

- Status: aceito
- Data: 2026-09-26

## Contexto

Ganho em pessoas (TC/Aglutinação) = `hrs_ganhas / ch_mensal`, e o R$ trabalhista sai
dele (`* custo`). A carga do dbt vinha só de `mel_carga_horaria`, chave (setor, mês):

- só existe a partir de 2024-09, então o ganho em pessoas de 2021 a 2024-08 zerava;
- tem setores com 0 (`Fábrica 04`, `Engenharia e Qualidade Cra`, `Impregnação Cra`,
  `Embalagem F7/F8` etc.), que também zeravam em silêncio.

O Qlik, fonte oficial de 2021-2025, usava a planilha `carga_horaria.xlsx` com chave
`estabelecimento | Area | mes ano` (Area = macro setor), de 2015 a 2026. Com ela a
cobertura das linhas TC de 2021-2025 sobe para 93-99%.

## Decisão

1. **Tabela aux `mel_carga_horaria_macro`** (estabelecimento, area, mes, ch_mensal),
   PK natural nas três primeiras. Carga manual (ADR 0004) pelo SQL gerado por
   `dags/melhorias/scripts/carga_horaria_macro.py` a partir da planilha: texto
   aparado, mês truncado no dia 1, duplicata exata descartada, chave repetida com
   valor diferente ou carga <= 0 falha (corrigir a planilha).
2. **Corte do histórico Qlik = var dbt `volume_hist_ate`** (`2026-01-01`), a mesma
   que corta o volume real histórico (planilhas do Qlik até o corte,
   `mel_volume_real` depois).
3. **Regra da carga, resolvida uma vez em `int_ganhos_calc`** (serve realizado e
   previsto), no mês de `dt_base` (= `dt_fap` no realizado):
   - `dt_base < volume_hist_ate`: só macro (filial, macro_setor, mês) — paridade
     com o Qlik, mesmo quando existe carga por setor;
   - `dt_base >= volume_hist_ate`: setor; nula ou 0 cai no macro.
4. **Taxa pelo mês de `dt_fap` em todos os offsets** (mantém ADR 0003). O Qlik
   convertia o offset 2 com a taxa do mês de `dt_fap`+30; a diferença é pequena e
   foi aceita.
5. **Teste `assert_ganho_tc_com_carga_horaria` (warn)**: lista linhas TC/Aglutinação
   aprovadas com horas ganhas e carga nula/0 nas duas fontes, em vez de deixar o
   ganho virar 0 sem aviso. Warn, não error: o buraco é de cadastro do negócio.

## Consequências

- Pré-requisito de deploy: `dbo.mel_carga_horaria_macro` existir antes do
  `dbt build` (a view de staging falha sem a tabela).
- O que continua sem carga: `macro_setor` nulo (Crato) e áreas fora da planilha
  (ex.: Fortaleza Corte, Crato Compostagem, Sobral Área de apoio). O warn aponta.
- Custo do funcionário não muda: `mel_custo_funcionario` já bate com a planilha do
  Qlik (diferença máxima 0,005).
- Mudar o corte é mudar a var; nenhuma data fica fixa nos models.

## Alternativas consideradas

- **Macro sempre (também depois do corte)**: descartaria a carga por setor que o
  negócio mantém desde 2024-09, mais fina que a do macro setor.
- **Fallback macro também antes do corte só quando o setor faltar**: 2024-09..2025
  deixaria de bater com o número oficial do Qlik.
- **Carregar a planilha em `mel_carga_horaria`**: chaves diferentes (setor vs
  macro setor) na mesma tabela quebrariam a unicidade e a semântica da coluna.
