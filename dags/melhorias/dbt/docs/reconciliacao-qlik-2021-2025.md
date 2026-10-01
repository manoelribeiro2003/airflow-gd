# Reconciliação dos ganhos 2021-2025: dbt vs planilhas do Qlik

- Issues: #21, #28 e #29 (tipos com volume), #25 e #27 (tipos "Outros")
- Data: 2026-09-28, revisado em 2026-09-29 (#27) e em 2026-09-30 (#28 e #29)
- Estado do dbt: produção de 2026-09-30, depois de #18 (volume histórico, ADR 0007), #19
  (carga macro, ADR 0006), #20 e #25 (FAPs ausentes, ADR 0008), #23, #24, #26 (ADR
  0010), #27 (ajuste de cadastro e FAPs de 2021 fora da carga, ADR 0011), #28 (mapa de
  macro setor e zero à esquerda do número da FAP, ADR 0012) e #29 (ganho pela planilha
  nas FAPs com cadastro incompleto ou divergente, ADR 0013), mais a correção de código
  de 16 dígitos da #21 (ver "Correções aplicadas").

## Método

- **Planilha (referência):** cálculo direto nas linhas das planilhas
  `BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx` (aba `BASE_LANCAMENTO`), com a carga
  horária e o custo das planilhas do Qlik, offsets 1 e 2. O ano é o da `Data da FAP`
  do arquivo normal (offset 1), o mesmo `dt_fap` que o dbt usa. O offset 2 fica no ano
  da FAP, mesmo quando a linha do `mês.anterior` cai no ano seguinte.
- **dbt:** `int_ganhos_long` e `int_ganhos_calc` de produção, agregados no grão da
  `fct_ganhos`: pessoas = horas / `ch_mensal`, R$ TC = pessoas × custo, R$ MP = consumo +
  troca MP. Ano de `dt_fap`, offsets 1 e 2.
- Tipos com volume: Tempo Ciclo e Aglutinação (TC), Consumo e Troca de Matéria Prima
  (MP). Os demais tipos ("Outros") têm seção própria no fim.
- Comparação por FAP e offset, para atribuir cada diferença a uma causa.

A primeira versão deste documento agrupava a planilha por `year(Data da FAP - 30)` no
offset 2. As linhas do `mês.anterior` com `Data da FAP` +60 dias (erro da planilha,
tratado como +30) de dez/2022 caíam em 2023, e a tabela ficava com 2022 e 2023 trocando
cerca de 20 pessoas. A tabela abaixo usa o ano de `dt_fap` nos dois lados.

Na revisão da #28 o lado da planilha de TC foi recalculado junto com o do dbt. Ficou
até 1,4 pessoa (0,2%) abaixo da versão anterior em 2021-2023; os valores de MP não
mudaram.

## Resultado por ano (TC e MP)

| Ano | Pessoas planilha | Pessoas dbt | Dif. | R$ TC planilha | R$ TC dbt | Dif. | R$ MP planilha | R$ MP dbt | Dif. |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 947,3 | 947,4 | 0,0% | 1.696.453 | 1.693.757 | -0,2% | 2.156.268 | 2.069.991 | -4,0% |
| 2022 | 778,4 | 781,5 | +0,4% | 1.570.330 | 1.573.358 | +0,2% | 3.464.857 | 3.464.745 | 0,0% |
| 2023 | 659,8 | 691,4 | +4,8% | 1.407.715 | 1.460.366 | +3,7% | 2.511.788 | 2.512.459 | 0,0% |
| 2024 | 1.296,8 | 1.268,8 | -2,2% | 3.062.286 | 3.009.593 | -1,7% | 3.038.626 | 3.039.590 | 0,0% |
| 2025 | 1.594,7 | 1.617,0 | +1,4% | 3.971.170 | 4.005.975 | +0,9% | 3.091.268 | 3.077.971 | -0,4% |

Horas ganhas ficam dentro de ±2% em todos os anos (2021: 0,0%; 2022: -0,1%; 2023:
+1,8%; 2024: -0,6%; 2025: +1,3%). As diferenças de 2% ou mais estão explicadas item a
item abaixo; nenhuma vem de regra de cálculo divergente.

2023 ficou mais longe da planilha depois da #28 (+2,6% para +4,8% em pessoas). Antes, a
falta de carga de Crato (-14,5 pessoas) compensava parte de duas diferenças para cima: a
taxa do offset 2 e uma FAP cancelada que a planilha lança com ganho negativo.

### Por tipo (offsets 1+2)

| Ano | Tipo | Horas | Pessoas | R$ |
|---|---|---|---|---|
| 2021 | Tempo Ciclo | 0,0% | 0,0% | -0,2% |
| 2021 | Aglutinação | 0,0% | +0,2% | -0,1% |
| 2021 | Consumo | | | +0,1% |
| 2021 | Troca MP | | | -6,4% |
| 2022 | Tempo Ciclo | -0,1% | +0,4% | +0,2% |
| 2022 | Aglutinação | 0,0% | +0,4% | +0,1% |
| 2022 | Consumo | | | 0,0% |
| 2022 | Troca MP | | | 0,0% |
| 2023 | Tempo Ciclo | +1,8% | +4,8% | +3,7% |
| 2023 | Aglutinação | 0,0% | -0,1% | +0,7% |
| 2023 | Consumo | | | +0,2% |
| 2023 | Troca MP | | | -0,1% |
| 2024 | Tempo Ciclo | -0,6% | -2,2% | -1,7% |
| 2024 | Aglutinação | 0,0% | -0,1% | -0,3% |
| 2024 | Consumo | | | +0,1% |
| 2024 | Troca MP | | | 0,0% |
| 2025 | Tempo Ciclo | +1,4% | +1,4% | +0,9% |
| 2025 | Aglutinação | 0,0% | +0,8% | +0,7% |
| 2025 | Consumo | | | +1,6% |
| 2025 | Troca MP | | | -4,7% |

## Correções aplicadas

### Código de produto acima de 2^53 (#21)

Códigos de 16 dígitos (MP do Laboratório F4, `90...0008`) passam de 2^53. Nas planilhas
de 2021 a 2023 eles foram gravados como double e perderam o último dígito ímpar:
`mel_ganhos` tem `9027051600060009`, a planilha e `mel_volume_real_hist` têm
`9027051600060008`. O join de volume falhava e o ganho ficava 0: 415 FAPs, nenhum código
de 16 dígitos casava em 2022.

`int_ganhos_calc` passa a tentar, quando o código exato não casa, o código de
`mel_ganhos` arredondado pelo mesmo double (`cod_prod_hist_float`). A partir de 2024 as
planilhas guardam o código exato, por isso o exato tem prioridade. Nenhuma FAP tem dois
códigos que arredondam para o mesmo valor. Efeito (offsets 1+2):

| Ano | Troca MP | Horas TC |
|---|---|---|
| 2021 | +88.540 | +68 |
| 2022 | +179.048 | +676 |
| 2023 | +377.966 | +844 |
| 2024 | +2.852 | -8 |

### Macro setor nulo e zero à esquerda do número da FAP (#28)

Em `mel_ganhos` e `mel_ganhos_hist`, 3.249 linhas não tinham `macro_setor` (quase todas
de Crato, 2021-2024). Sem macro setor a linha não acha carga horária e o ganho de TC
fica 0. `stg_mel_ganhos` passa a preencher o macro nulo pelo seed `mel_macro_setor` (44
pares filial e setor); o macro cadastrado não muda. Sobram 5 linhas sem macro, todas
sem setor.

Em `mel_volume_real_hist`, 6 FAPs estavam sem o zero inicial que o Excel tirou da célula
numérica, e o volume do offset 2 de 4 delas (2024) não casava com `mel_ganhos`. O script
repõe o zero e a tabela foi recarregada. Decisões na ADR 0012.

Efeito medido em `fct_ganhos` (build de produção de 2026-09-30, antes e depois; offsets
1+2, 562 FAPs):

| Ano | Pessoas | R$ TC | Origem |
|---|---|---|---|
| 2021 | +34,2 | +60.809 | mapa |
| 2022 | +25,2 | +47.683 | mapa |
| 2023 | +14,5 | +28.694 | mapa |
| 2024 | +47,0 | +106.196 | mapa (+45,2 e +101.804) e zero da FAP (+1,8 e +4.391) |

2025 e 2026 não mudaram. Nenhuma linha entrou ou saiu de `fct_ganhos`, e
`fct_aderencia.atingiu_meta` não mudou. O ganho previsto do quadrimestre
(`int_ganhos_previsto`) subiu R$ 629.556 em 618 FAPs de 2021-2024. O warn
`assert_ganho_tc_com_carga_horaria` caiu de 1.256 para 599 linhas.

### Cadastro incompleto ou divergente da planilha (#29)

Em 31 FAPs de Tempo Ciclo, Consumo e Troca MP o cadastro em `mel_ganhos` não bate com a
planilha: 24 têm um código no cadastro e vários na planilha (31032021080501: 1 contra
200), e 7 têm componente diferente (consumo 100 vezes menor, custo par anterior igual ao
atual, mix somando mais de 100%, linha sem código). O negócio decidiu que a planilha
vale. O seed `mel_ganhos_fonte_planilha` lista essas FAPs; `stg_mel_ganhos` tira as
linhas delas do bronze e usa as da planilha, carregadas em `mel_ganhos_hist`. Filial,
setor e idealizador continuam os do SharePoint. Decisões na ADR 0013.

Efeito medido em `fct_ganhos` (build de produção de 2026-09-30, antes e depois; offsets
1+2):

| Ano | FAPs | Pessoas | R$ TC | R$ MP |
|---|---|---|---|---|
| 2021 | 4 | +14,7 | +26.252 | |
| 2022 | 12 | +2,2 | +4.482 | +233.526 |
| 2023 | 2 | | | +21.699 |
| 2024 | 12 | +15,8 | +36.788 | +15.415 |
| 2025 | 1 | | | -18.728 |

As 31 FAPs passam a bater com a planilha em horas e em R$ de MP. O ganho previsto delas
vira 0, como nas demais FAPs do hist: `ganho_reais_previsto_quadrimestre` cai R$ 501.402
em 11 FAPs de `fct_melhoria`.

Fora das 31 FAPs nada mudou. Nenhuma linha entrou ou saiu de `fct_ganhos`,
`fct_melhoria` e `fct_aderencia`; os offsets 3 e 4 seguem iguais. Em `fct_aderencia`,
`ganho_total` mudou em 17 linhas (idealizador e bimestre), e `realizado_qtde` e
`atingiu_meta` não mudaram. Em `fct_ganhos` o dia de `dt_competencia` mudou em 8 FAPs
(a `Data da FAP` da planilha); o mês, em nenhuma.

24032024100212 e 31032024100202, que a issue deixou para investigar, não entram: a
terceira linha tem mix 100 na planilha e 50 em `mel_ganhos` (a planilha soma 150%), e o
negócio decidiu que vale o SharePoint.

## Diferenças remanescentes, item a item

### Pessoas de TC (dbt - planilha)

| Causa | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| Sem carga horária no dbt | 0,0 | 0,0 | 0,0 | 0,0 | -3,0 |
| Taxa do offset 2 | +0,1 | +3,6 | +21,5 | -18,9 | +3,1 |
| Taxa do offset 1 | 0,0 | 0,0 | -0,9 | +0,1 | -1,2 |
| Volume diferente (cadastro) | 0,0 | -0,5 | 0,0 | -4,5 | +0,2 |
| FAP só na planilha | 0,0 | 0,0 | +11,1 | -4,6 | -0,5 |
| Offset 2 das FAPs de dez/2025 | 0,0 | 0,0 | 0,0 | 0,0 | +23,6 |
| **Total** | **+0,1** | **+3,1** | **+31,6** | **-28,0** | **+22,3** |

As parcelas podem diferir do total em 0,1 por arredondamento.

- **Sem carga horária no dbt:** 6 FAPs de Crato Compostagem de out/2025. O macro setor
  existe, mas `mel_carga_horaria_macro` só tem carga de Compostagem a partir de
  nov/2025. A planilha conta essas FAPs no offset 2, com a carga de novembro. Antes da
  #28 esta linha somava cerca de -120 pessoas em 2021-2025.
- **TC sem carga nos dois lados:** 187 FAPs aprovadas de 2021-2025 têm horas ganhas e
  nenhuma carga horária do macro setor no mês (warn `assert_ganho_tc_com_carga_horaria`).
  A planilha também dá 0, então não aparecem como diferença, mas o ganho em pessoas
  delas não é contado: Crato Compostagem (77 FAPs), Fortaleza Corte (55), Frequência
  (33) e Matrizaria (13), Sobral Área de apoio (5), Crato Pré-Montagem (3) e Engenharia
  e Qualidade (1). Lista em `reconciliacao/tc_sem_carga_2021_2025.csv`.
- **Taxa do offset 2:** a planilha usa a carga horária do mês de `Data da FAP` + 30
  dias; o dbt usa a do mês de `dt_fap` para todos os offsets (ADR 0003, decisão
  mantida). Inclui 153 FAPs de Crato que estavam sem carga antes da #28 e passaram a
  ter ganho, com essa diferença de taxa no offset 2.
- **Taxa do offset 1:** 43 FAPs em que a `Data da FAP` da planilha cai em mês diferente
  do `dt_fap` (exemplo: 24032025022801, março na planilha e fevereiro no dbt), e a
  carga horária muda de um mês para o outro.
- **Volume diferente:** o cadastro em `mel_ganhos` tem menos códigos ou outro mix que a
  planilha. As 17 FAPs de TC da #29 saíram desta linha (antes -14,8 em 2021, -2,7 em
  2022 e -20,3 em 2024). Ficam, por decisão do negócio:
  - 24032024100212 (-1,2) e 31032024100202 (-1,1): mix da terceira linha 100 na
    planilha e 50 no SharePoint; vale o SharePoint. 24032024100213 e 31032024100203
    (-0,3 cada) têm o mesmo mix;
  - 30032022110901 e 29032022092301 (-0,2 cada) e 30032022092303 (-0,1): um código no
    cadastro, 13 a 61 na planilha; fora do seed.
- **FAP só na planilha:** a FAP não conta no dbt (ver MP abaixo). Em 2023 o valor é
  positivo porque 02032023110703 (Cancelado) está lançada na planilha com ganho
  negativo (-11,3 pessoas).
- **Offset 2 das FAPs de dez/2025:** 1.313 FAPs. O offset 2 delas é jan/2026, que o dbt
  lê de `mel_volume_real` (ADR 0007). A planilha de 2025 não tem esse mês: ele estaria
  no `mês.anterior` de 2026, que não existe. Não são FAPs fora da planilha.

### R$ MP (dbt - planilha)

| Causa | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| FAP só na planilha | -86.234 | 0 | 0 | -37 | -61.464 |
| Offset 2 das FAPs de dez/2025 | 0 | 0 | 0 | 0 | +48.294 |
| Cadastro diferente | -43 | -111 | +671 | +1.001 | -128 |

- **FAP só na planilha:** 54 FAPs de TC e MP (2021-2025) ficam fora do dbt, que só
  conta FAP aprovada (ADR 0003):
  - 2021: 29 FAPs de MP (26 Troca MP, 3 Consumo). São 28 sem registro em nenhum export
    do SharePoint, descartadas (ADR 0011), e 1 reprovada. As demais FAPs
    de 2021 que faltavam em `mel_aprovacao` (175 de TC e MP, criadas em dez/2020 ou
    aprovadas sem data) foram carregadas na #27 e batem com a planilha.
  - 2022-2025: 25 FAPs sem aprovação, reprovadas, canceladas, com aprovação expirada ou
    com outro tipo em `mel_ganhos`. Em 2025, 2 FAPs de Troca MP (R$ 61 mil).
  - Entre elas, 9 FAPs têm ganho na planilha e não existem em `mel_aprovacao` nem em
    `mel_ganhos`: 24032024123104, 02032024100212, 25032024120408, 21032024122003,
    02032024120305 e 02032024092701 (2024, -4,6 pessoas), 31072025120420 e
    31072025120412 (Troca MP de dez/2025, R$ 61 mil) e 61032023091801 (2023, 0,1
    pessoa). O negócio decidiu na #29 que FAP fora de `mel_aprovacao` é descartada (ADR
    0013).
- **Cadastro diferente:** as 14 FAPs de Consumo e Troca MP da #29 saíram desta linha
  (antes -233.637 em 2022, -21.028 em 2023, -14.415 em 2024 e +18.600 em 2025). As
  maiores eram 26082022092801 (-140.654), 26032022111702 (-69.541), 96072023042401/02
  (-21.699) e 03072025060408 (+18.728). Sobram FAPs fora do seed com diferença pequena
  de componente: 46082023092001 (+1.819), 71072023080201 e 71072023080203 (-583 e
  -580), 25082025052701 (-571) e 26082021120303 (-301); as demais ficam abaixo de
  R$ 300 por FAP.

O que sobra em "FAP só na planilha" não tem correção no dbt: a FAP não está aprovada em
`mel_aprovacao`.

## Tipos "Outros" (sem volume)

Administrativas, FAO, Manutenção, Eficiência energética, Acondicionamento e os demais
tipos sem volume. O ganho é o `Ganho mês R$` cadastrado (`ganho_previsto`), igual em
todos os offsets. Comparação: `fct_ganhos` offset 1 (bronze + `mel_ganhos_hist`) contra o
`R$ Mês` cacheado das planilhas, por FAP. Só arquivos normais; FAP em mais de um arquivo
usa o mais recente. Ano de `Data da FAP`.

| Ano | Planilha | dbt | Diferença |
|---|---|---|---|
| 2021 | 3.503.586 | 3.451.346 | 52.240 |
| 2022 | 7.857.682 | 7.857.646 | 36 |
| 2023 | 6.232.482 | 6.158.156 | 74.325 |
| 2024 | 4.250.578 | 4.251.046 | -468 |
| 2025 | 5.640.231 | 5.635.157 | 5.075 |

| Caso | FAPs | Planilha | dbt | Diferença |
|---|---|---|---|---|
| Bate (até 1 centavo) | 28.713 | 27.271.418 | 27.271.418 | 0 |
| Linha duplicada na planilha | 34 | 162.127 | 81.064 | 81.064 |
| Sem registro em nenhum export (descartadas) | 13 | 26.698 | 0 | 26.698 |
| Reprovada ou aprovação expirada | 10 | 24.317 | 0 | 24.317 |
| Valor do dbt mantido | 2 | 0 | 868 | -868 |
| Só no dbt | 1 | 0 | 0,20 | -0,20 |

- **Linha duplicada na planilha:** a mesma linha repetida no mesmo arquivo (FAO de 2023
  quase todas). A planilha e o Qlik somavam o ganho em dobro; o dbt conta uma vez, e o
  hist deduplica pela mesma regra (ADR 0008). Linhas da mesma FAP com ganhos diferentes
  (um lançamento por posto) somam (ADR 0011).
- **Descartadas:** 13 FAPs de 2021 que não existem em nenhum export do SharePoint, entre
  elas 93022021042401 (Saúde e Segurança, R$ 20.400) e 18102021060201 (Gestão de
  resíduos, R$ 3.464). ADR 0011.
- **Reprovada ou expirada:** fora pela regra da ADR 0003 (#24).
- **Valor do dbt mantido:** 141102024070102 (a fórmula de `R$ Mês` na linha da planilha
  aponta para a coluna errada e dá 0; o `Ganho mês R$` é 468, igual ao dbt) e
  02032025021201 (Tempo Ciclo no cadastro, sem tipo na planilha; o dbt calcula R$ 400,45
  pelas horas).
- **Só no dbt:** 26112025021201 (Acondicionamento, R$ 0,20) não está na planilha.
- **Cadastro ajustado só na planilha:** 9 FAPs em que a área corrigiu o ganho na planilha
  e não no SharePoint já batem, pelo seed `mel_ganhos_ajuste` (ADR 0011).

As FAPs "Outros" do hist (#25 e #27) mudaram o realizado e a aderência de 2021 e 2023:
`fct_aderencia.atingiu_meta` subiu cerca de 1.950 (+1.933 na #25, +18 na #27). O
aumento foi confirmado como esperado pelo negócio.

## Outros pontos registrados

- **Ano de competência:** o Qlik soma por mês de `Data da FAP` do lançamento (dez do
  ano Y cai em jan de Y+1 no `mês.anterior`); o dbt soma por mês de competência a partir
  de `dt_fap`. Por ano de competência isso move cerca de ±20 pessoas entre anos
  vizinhos, sem mudar o total. As tabelas acima usam o ano de `dt_fap` nos dois lados.
- **Offsets 3 e 4:** em 2021-2025 o dbt tem 0 nesses offsets nos tipos com volume (o
  histórico só tem 1 e 2), igual à planilha.
- **A partir de 2026:** o volume vem de `mel_volume_real` (parquet do SharePoint), não
  mais das planilhas (`volume_hist_ate`, ADR 0007). Na sobreposição 2025-05 a 2025-12 a
  planilha tinha cerca de 15% mais horas que o parquet, então 2026 não é comparável com
  a série do Qlik sem esse ajuste.

## Ações para o negócio

1. Informar a carga horária que falta em `mel_carga_horaria_macro` para as FAPs de
   `reconciliacao/tc_sem_carga_2021_2025.csv` (187 FAPs). Crato Compostagem e
   Pré-Montagem e Fortaleza Corte e Frequência só têm carga a partir de nov/2025;
   Fortaleza Matrizaria, Sobral Área de apoio e Crato Engenharia e Qualidade não têm
   nenhuma. Só as 6 FAPs de Compostagem de out/2025 têm ganho na planilha (3,0
   pessoas). Setor novo com `macro_setor` nulo entra no seed `mel_macro_setor` (ADR
   0012).
2. Cadastro diferente da planilha: decidido na #29 que a planilha vale. FAP nova com o
   mesmo problema entra no seed `mel_ganhos_fonte_planilha` (tipos com volume, ADR
   0013) ou no `mel_ganhos_ajuste` (tipos sem volume, ADR 0011). As FAPs que sobraram
   em "Volume diferente" ficam como estão; as de "Cadastro diferente" de MP (abaixo de
   R$ 2 mil por FAP) não foram revistas.
3. Revisar os idealizadores sem meta no bimestre da FAP (warn de `sk_idealizador` em
   `fct_ganhos`, 183 FAPs, 151 de 2021).
