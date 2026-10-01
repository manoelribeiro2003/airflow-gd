# 0008 — Ganhos de FAPs aprovadas ausentes de `mel_ganhos` via planilhas do Qlik

- Status: aceito
- Data: 2026-09-26
- Atualizado: 2026-09-29 (issue #25, tipos sem ganho por volume)
- Atualizado: 2026-09-29 (issue #27, ganhos diferentes na mesma FAP somam; ADR 0011)
- Atualizado: 2026-09-30 (issue #29, FAPs de `mel_ganhos_fonte_planilha` e linha sem
  código; ADR 0013)

## Contexto

Parte das FAPs de Tempo Ciclo, Aglutinação, Consumo e Troca MP está `Aprovado` em
`mel_aprovacao` e aparece nas planilhas `BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx`
(aba `BASE_LANCAMENTO`) que alimentavam o Qlik, mas não tem nenhuma linha em
`mel_ganhos`. Sem componentes, o dbt não calcula ganho nenhum para elas, mesmo com o
volume real já disponível em `mel_volume_real_hist` (ADR 0007). O dado de ganho
(código, TC, consumo, custo par, mix, idealizador) só existe na planilha.

No snapshot de 2026-09-23 (`mel_aprovacao` + `mel_ganhos` com a importação dos
faltantes) são 5.759 FAPs com linhas na planilha, 16.897 linhas: 4.676 FAPs de 2021,
1.054 de 2023 e 29 de 2024-2025. A issue #20 estimava ~2.030 FAPs; a contagem por tipo
(TC 1.834 + Aglutinação 26 em 2021, TC 395 em 2023) não fecha com aquela estimativa,
mas o ganho em pessoas sim (ver Consequências).

Comparando a planilha com `mel_ganhos` nas FAPs presentes nas duas: MIX, TC, consumo,
custo par e preço MP têm a mesma unidade (razão mediana 1,0); o crachá da planilha é
igual ao de `mel_ganhos` em 99,9% das linhas; o bimestre de `Data da FAP` é igual ao de
`mel_ganhos.dt_fap` em ~98%. Nas FAPs ausentes, `mel_aprovacao.cracha_idealizador` é
nulo em todas as de 2021.

O mesmo acontece com FAPs aprovadas dos demais tipos (Administrativas, FAO, Manutenção,
Logística, Qualidade...), cujo ganho não depende de volume: a planilha tem o ganho do
mês 1 pronto em `Ganho mês R$` (a coluna `R$ Mês` do Qlik é `VALUE(Ganho mês R$)`). Em
`mel_ganhos` esses tipos têm uma linha por FAP, quase sempre sem código, e o ganho em
`ganho_previsto` (macro `ganho_reais_case`). Nas planilhas 2021-2024, `Ganho mês R$` está
gravado como texto pt-BR (`"40286,88"`); `pd.to_numeric(errors='coerce')` transforma
isso em NaN. Algumas FAPs têm a mesma linha repetida no arquivo, com o mesmo ganho, e o
Qlik somava o ganho em dobro.

## Decisão

1. **Tabela aux `mel_ganhos_hist`**, com os campos de ganho e idealizador da planilha,
   nos tipos e collation de `mel_ganhos`. Carga manual (ADR 0004) pelo SQL gerado por
   `dags/melhorias/scripts/ganhos_hist.py`, que recebe as planilhas e a lista de FAPs
   aprovadas sem linha em `mel_ganhos` (query no docstring do script):
   - só linhas com tipo de melhoria e só de arquivos normais (o `mês.anterior` repete
     as linhas com a data deslocada e só serve de volume do offset 2);
   - FAP em mais de um arquivo normal (dez/2024 em 2024 e 2025): a FAP inteira vem do
     arquivo mais recente;
   - tipos com ganho por volume (TC, Aglutinação, Consumo, Troca MP): grão da planilha
     (linha por operação/mix), sem deduplicar, porque o Qlik somava todas; linha sem
     código fica com `cod_prod` = `SEM_CODIGO` (ADR 0013; antes caía); `ganho_previsto`
     nulo;
   - demais tipos: uma linha por FAP, `ganho_previsto` = `Ganho mês R$` (texto pt-BR
     com vírgula decimal ou número; texto que não é número para o script). O ganho é da
     FAP, não do componente: linha repetida não soma de novo, e linhas da mesma FAP com
     ganhos diferentes somam (ADR 0011; antes paravam o script). `cod_prod` pode ser nulo, como em `mel_ganhos`;
   - `cod_prod` sem zeros à esquerda, igual a `mel_volume_real_hist`;
   - `dt_fap` = `Data da FAP` do arquivo normal (o offset do volume é relativo a ela);
   - atributos da FAP (data, filial, setor, macro setor, idealizador, cargo, origem,
     replicação) iguais em todas as linhas: a menor data e, nos demais, o primeiro
     valor não nulo. `fct_ganhos` agrupa por eles; valor diferente entre linhas
     duplicaria a FAP no mês (1 FAP de 2021 tem duas datas na planilha).
2. **`stg_mel_ganhos` = bronze `union all` hist**, com a coluna `fonte`
   (`bronze`|`hist`) e unicidade por (`fonte`, `id`). O que a planilha não tem vem de
   `mel_aprovacao`: `id_solicitacao_assinatura`, `tipo_fap`, `fabrica`, `gerente`,
   `cc_idealizador`, `created`/`modified`, e crachá/nome/gerente do idealizador e
   `dt_fap` quando a planilha está vazia. Sem volume previsto (`volume_mes_*`) nem
   `investimento`: a planilha só tem o volume real. `ganho_previsto` vem do hist (só
   nos tipos sem volume).
3. **Uma FAP nunca está nas duas fontes.** A exceção são as FAPs do seed
   `mel_ganhos_fonte_planilha` (ADR 0013): têm linha em `mel_ganhos` e no hist, e
   `stg_mel_ganhos` tira as do bronze. Três barreiras:
   - o script só leva FAP da lista;
   - o SQL gerado confere, antes do commit, se alguma FAP já tem linha em `mel_ganhos`
     ou não está aprovada, e desfaz a carga com `throw` (a lista pode ter ficado velha);
   - os testes dbt `assert_mel_ganhos_hist_disjunto` e
     `assert_mel_ganhos_hist_aprovada` quebram o build se o bronze passar a ter a FAP ou
     se ela deixar de estar aprovada.
   O teste `assert_mel_ganhos_hist_grao` garante uma linha por FAP nos tipos sem volume
   e `ganho_previsto` nulo nos tipos com volume.
4. O volume realizado dessas FAPs vem de `mel_volume_real_hist` pelo mesmo caminho das
   demais (`int_ganhos_calc`, ADR 0007); nenhum model abaixo de `stg_mel_ganhos` muda.

## Consequências

- Pré-requisito de deploy: `dbo.mel_ganhos_hist` existir antes do `dbt build` (a view
  `stg_mel_ganhos` falha sem a tabela). Na #25, a tabela ganhou `ganho_previsto` e
  `cod_prod` passou a aceitar nulo; o SQL gerado migra a tabela antiga (`alter table`)
  e precisa rodar antes do `dbt build`.
- A lista de FAPs sai do estado atual de `mel_aprovacao`/`mel_ganhos`. As FAPs de 2021 e
  2023 só existem em `mel_aprovacao` depois da importação dos faltantes do SharePoint
  (no snapshot anterior a ela a query devolve 69 FAPs, 39 delas nas planilhas, todas de
  2025). Gerar a lista depois dessa importação.
- Ganho recuperado no offset 1, calculado localmente com as regras de
  `int_ganhos_calc` (volume de `mel_volume_real_hist`, carga macro do mês de dt_fap):

  | Ano | FAPs | Horas | Pessoas | R$ MP (Consumo + Troca) |
  |---|---|---|---|---|
  | 2021 | 4.676 | 55.293 | 322,7 | 296.279 |
  | 2023 | 1.054 | 15.555 | 91,4 | 448.732 |
  | 2024 | 3 | 156 | 0,8 | 46 |
  | 2025 | 24 | 130 | 0,7 | 866 |

  A issue #20 esperava ~330 pessoas em 2021 e ~90 em 2023.
- Ganho dos tipos sem volume (issue #25, `Ganho mês R$` no mês 1; lista de FAPs de
  2026-09-29):

  | Ano | FAPs | FAPs com ganho | R$ |
  |---|---|---|---|
  | 2021 | 3.095 | 1.315 | 1.184.137 |
  | 2023 | 927 | 450 | 949.666 |
  | 2024 | 1 | 1 | 1.155 |
  | 2025 | 8 | 4 | 6.494 |

  Mais 2 FAPs sem `Data da FAP` na planilha (R$ 1.233; a data vem de `mel_aprovacao`).
  A deduplicação tira R$ 636 de 13 FAPs de 2021 com a linha repetida.
- As FAPs passam a aparecer em `fct_ganhos`, `fct_melhoria` (ganho realizado,
  `resultado_fap`), `int_melhorias_realizado` e `fct_aderencia`, com o bimestre de
  `Data da FAP` e o crachá da planilha.
- O ganho previsto das FAPs de tipos com volume em `fct_melhoria` é 0 (não há
  estimativa). Nos demais tipos, previsto = realizado do mês 1, como no bronze.
- `fct_melhoria` continua tirando `bimestre` e `sk_idealizador` de `mel_aprovacao`, sem
  crachá nas FAPs de 2021: nelas a chave fica `bimestre|` e, em ~2% das FAPs, o
  bimestre difere do de `fct_ganhos` (data da aprovação vs `Data da FAP`). Corrigir
  exige mudar a fonte de `fct_melhoria` para todas as FAPs; fica fora deste escopo.
- Se o app voltar a gravar uma dessas FAPs em `mel_ganhos`, o build quebra no teste de
  disjunção até alguém gerar a lista de novo e recarregar `mel_ganhos_hist`. É de
  propósito: silenciosamente, o ganho da FAP contaria duas vezes.

## Alternativas consideradas

- **Inserir em `mel_ganhos` com `insert_manual`** (DAG `MANUAL_MELHORIAS_GANHOS_PLANILHA`):
  mistura dado do Qlik com o bronze ingerido do SharePoint e some com a origem; o
  bronze é imutável.
- **Deduplicar no staging (bronze ganha do hist)** em vez de testar: esconderia a
  sobreposição, e o hist ficaria com linhas mortas sem ninguém perceber.
- **Grão da planilha também nos tipos sem volume**: reproduziria a soma em dobro do
  Qlik nas FAPs com linha repetida; `Ganho mês R$` é por FAP e o bronze tem uma linha
  por FAP nesses tipos.
- **`dt_fap` de `mel_aprovacao`**: difere da planilha em parte das FAPs; o offset do
  volume real (`mel_volume_real_hist`) é relativo à `Data da FAP` da planilha, que era a
  data usada pelo Qlik.
- **Idealizador de `mel_aprovacao`**: vazio em todas as FAPs de 2021; a planilha é igual
  a `mel_ganhos` onde as duas existem.
