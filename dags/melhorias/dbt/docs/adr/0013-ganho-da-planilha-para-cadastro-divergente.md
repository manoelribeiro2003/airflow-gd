# 0013 — Ganho de TC e MP pela planilha quando o cadastro da FAP diverge

- Status: aceito
- Data: 2026-09-30
- Issue: #29
- Complementa: [ADR 0008](0008-ganhos-historicos-faps-ausentes-planilhas-qlik.md)
  (`mel_ganhos_hist`) e [ADR 0011](0011-ajustes-cadastro-e-faps-2021-fora-da-carga.md)
  (ajuste de cadastro nos tipos sem volume)

## Contexto

A reconciliação com as planilhas do Qlik (`reconciliacao-qlik-2021-2025.md`) deixou
quatro grupos de FAPs de Tempo Ciclo, Consumo e Troca de Matéria Prima em que a
diferença vem do cadastro, não do cálculo.

**Cadastro incompleto (24 FAPs).** `mel_ganhos` tem um código de produto e a planilha
aplica a FAP a vários. Exemplos: 31032021080501 tem 1 código no cadastro e 200 na
planilha; 26082022092801 tem 76 contra 147. O volume real dos outros códigos existe em
`mel_volume_real_hist`, mas sem a linha de ganho o dbt não o usa.

**Cadastro divergente (7 FAPs).** O código existe nos dois lados, com componentes
diferentes: consumo 0,125 na planilha e 0,00125 em `mel_ganhos` (46082022100402), custo
par anterior igual ao atual no cadastro (96072023042401/02), mix somando 10.964 em 142
linhas (49082022100702), consumo por linha na planilha e um valor único no cadastro
(26032022111702). Em 30032021080410 a linha da planilha não tem código, e o cadastro
guarda o texto `Embalamento Favo Dedo` no lugar dele.

**Mix de 24032024100212 e 31032024100202.** A issue deixou as duas para investigar. A
causa é a terceira linha, com mix 100 na planilha e 50 em `mel_ganhos`: na planilha o
mix da FAP soma 150%, no cadastro soma 100%. A primeira também tem a data em setembro na
planilha e em outubro no cadastro.

**FAP só na planilha (9 FAPs de 2023 a 2025).** Têm ganho na planilha e não existem em
`mel_aprovacao` nem em `mel_ganhos`: 24032024123104, 02032024100212, 25032024120408,
21032024122003, 02032024120305, 02032024092701, 31072025120420, 31072025120412 e
61032023091801.

Decisão do negócio (2026-09-30): nos dois primeiros grupos a planilha está certa. Nas
duas FAPs de mix vale o SharePoint. FAP que não está em `mel_aprovacao` fica fora.

O seed `mel_ganhos_ajuste` (ADR 0011) não serve aqui. Ele troca um valor por FAP
(`ganho_previsto`), e nos tipos com volume o ganho sai de componentes por linha
multiplicados pelo volume real.

## Decisão

1. **Seed `mel_ganhos_fonte_planilha`** (`numero_fap`, `motivo`, `detalhe`), carregado à
   mão (ADR 0004), com PK em `numero_fap`. Lista as 31 FAPs dos dois primeiros grupos.
   `motivo` é `cadastro incompleto` ou `cadastro divergente`.
2. **As linhas de ganho dessas FAPs vêm de `mel_ganhos_hist`.** `ganhos_hist.py` soma as
   FAPs do seed à lista de FAPs sem linha em `mel_ganhos`, e a carga leva as linhas da
   planilha no mesmo grão das demais (ADR 0008).
3. **`stg_mel_ganhos` tira do bronze as FAPs do seed.** As linhas de `mel_ganhos`
   continuam na tabela, que não é alterada, e deixam de entrar no `union all`. A FAP
   segue vindo de uma fonte só.
4. **Atributos da FAP continuam os do SharePoint:** filial, setor, macro setor, crachá,
   nome e gerente do idealizador, cargo, origem e replicação saem das linhas de
   `mel_ganhos` da FAP (um valor por FAP). Da planilha vêm os componentes (código, TC,
   consumo, preço, custo par, mix) e a `Data da FAP`, porque o offset do volume real é
   relativo a ela.
5. **Exceção na disjunção da ADR 0008.** O `throw` 50001 do SQL de carga e o teste
   `assert_mel_ganhos_hist_disjunto` ignoram as FAPs do seed. O teste novo
   `assert_mel_ganhos_fonte_planilha_valido` falha se uma FAP do seed não tem linha em
   `mel_ganhos_hist` (ela sumiria do dbt) ou é de tipo sem volume (caso do
   `mel_ganhos_ajuste`). O build da DAG passa a rodar com `--indirect-selection
   cautious`: no modo padrão o `--exclude resource_type:seed` tira do build todo teste
   que lê um seed, e estes dois e o `assert_mel_ganhos_ajuste_valido` não rodariam.
6. **Linha sem código nos tipos com volume fica, com o código `SEM_CODIGO`**, em
   `mel_volume_real_hist` e em `mel_ganhos_hist`. Antes as duas cargas descartavam a
   linha. O Qlik calculava o ganho na própria linha, sem usar o código. São 6 FAPs com
   linha assim; só 30032021080410 tem ganho nela.
7. **24032024100212 e 31032024100202 ficam como estão**, com o mix do SharePoint. Não
   entram no seed.
8. **As 9 FAPs só na planilha ficam fora do dbt**, pela regra da ADR 0003. Nenhuma carga
   é feita para elas.

## Consequências

Efeito em `fct_ganhos`, offsets 1 e 2, dbt depois menos dbt antes, medido no build de
produção de 2026-09-30:

| Ano de `dt_fap` | FAPs | Pessoas | R$ TC | R$ MP |
|---|---|---|---|---|
| 2021 | 4 | +14,7 | +26.252 | |
| 2022 | 12 | +2,2 | +4.482 | +233.526 |
| 2023 | 2 | | | +21.699 |
| 2024 | 12 | +15,8 | +36.788 | +15.415 |
| 2025 | 1 | | | -18.728 |

- As 31 FAPs passam a bater com a planilha em horas e em R$ de MP. Em pessoas sobra
  -0,1 em 2021: o offset 2 de 61032021121704 cai em janeiro, e o dbt usa a carga horária
  do mês de `dt_fap` nos dois offsets (ADR 0003).
- 30032022092302 cai de 1,49 para 0,32 pessoa e 03072025060408 perde R$ 18.728: o
  cadastro dava mais ganho que a planilha.
- `mel_ganhos_hist` vai de 22.597 para 43.964 linhas (10.326 para 10.357 FAPs). As
  linhas novas são das 31 FAPs; 26082022092801 tem 13.864 e 26032022111702 tem 4.040. As
  linhas que já existiam não mudam. `mel_volume_real_hist` ganha 15 chaves `SEM_CODIGO`
  (194.972 para 194.987).
- O ganho previsto dessas FAPs vira 0, como nas demais do hist (ADR 0008): a planilha só
  tem volume real. Em `fct_melhoria`, `ganho_reais_previsto_quadrimestre` cai R$ 501.402
  em 11 FAPs (26082022092801 responde por R$ 289.188 e 03072025060408 por R$ 138.429). O
  previsto saía do mesmo cadastro que a decisão considera errado.
- `fct_ganhos` usa a `Data da FAP` da planilha nessas FAPs. Em 8 o dia muda; o mês não
  muda em nenhuma. `fct_melhoria` segue com bimestre e idealizador de `mel_aprovacao`.
- Fora das 31 FAPs nada muda: nenhuma linha entra ou sai de `fct_ganhos`, `fct_melhoria`
  e `fct_aderencia`, e `realizado_qtde` e `atingiu_meta` ficam iguais.
- As duas FAPs de mix seguem 2,3 pessoas abaixo da planilha em 2024. Outras 5 FAPs
  pequenas com o mesmo tipo de diferença ficaram fora do seed por decisão do negócio
  (-1,0 pessoa no total): 24032024100213 e 31032024100203 (mesmo mix), 29032022092301,
  30032022092303 e 30032022110901 (um código no cadastro, 13 a 61 na planilha).
- Ordem de deploy: carregar `dbo.mel_ganhos_fonte_planilha`, depois
  `mel_volume_real_hist`, depois `mel_ganhos_hist` (o `throw` 50001 lê o seed), e só
  então o `dbt build` desta versão. Sem a tabela do seed a view `stg_mel_ganhos` falha.
  Com `mel_ganhos_hist` carregada e o dbt na versão anterior, as 31 FAPs contam duas
  vezes e o teste de disjunção quebra o build; a carga e o deploy vão na mesma janela.
- FAP nova com o mesmo problema entra com uma linha no seed e uma recarga de
  `mel_ganhos_hist`. Tirar a FAP do seed sem recarregar o hist quebra o teste de
  disjunção; é de propósito.
- Se o cadastro for corrigido no SharePoint, a FAP continua vindo da planilha até sair
  do seed.

## Alternativas consideradas

- **Corrigir o cadastro no SharePoint:** é a correção na origem, mas depende da área
  para cadastrar centenas de códigos por FAP em FAPs de 2021 a 2025 (147 códigos em
  26082022092801). Se acontecer, a FAP sai do seed.
- **Deduplicar no staging sem seed** (hist ganha do bronze quando a FAP está nos dois):
  esconderia sobreposição acidental, que hoje quebra o build (ADR 0008).
- **Seed de componentes por linha** (como `mel_ganhos_ajuste`, por FAP e código): seriam
  21 mil linhas num CSV, duplicando o que `mel_ganhos_hist` já guarda com o mesmo grão.
- **Trazer também os atributos da FAP da planilha:** em 6 FAPs o crachá do idealizador
  da planilha difere do de `mel_ganhos` e `mel_aprovacao`, e o nome ao lado, na própria
  planilha, é o do crachá do SharePoint; em 12 o gerente difere; 26082022092801 tem três
  setores na planilha. A FAP mudaria de idealizador em `fct_ganhos` e não em
  `fct_melhoria`.
- **Carregar as 9 FAPs só da planilha em `mel_aprovacao`**, como na ADR 0011: lá as FAPs
  tinham registro em algum export do SharePoint. Estas não têm registro de aprovação.
- **Casar a linha sem código pelo nome do processo:** o texto do cadastro não segue
  padrão e não existe em `mel_volume_real_hist`.
