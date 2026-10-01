# 0011 — Ajuste de cadastro pela planilha e FAPs aprovadas de 2021 fora da carga

- Status: aceito
- Data: 2026-09-29
- Issue: #27
- Complementa: [ADR 0003](0003-contrato-gold-ganhos-long-dt-fap-aprovadas.md) (só FAP
  aprovada com `dt_fap`) e [ADR 0008](0008-ganhos-historicos-faps-ausentes-planilhas-qlik.md)
  (`mel_ganhos_hist`)

## Contexto

A reconciliação dos tipos "Outros" (#25) comparou o ganho do mês 1 do dbt com o
`R$ Mês` das planilhas `BASE_LANCAMENTO`. Sobraram dois grupos de diferença que não
vêm de regra de cálculo.

**Cadastro divergente no bronze.** Em 12 FAPs, `mel_ganhos.ganho_previsto` difere do
`Ganho mês R$` da planilha. A área confirmou que o valor certo é o da planilha: o dado
foi ajustado depois do cadastro, só na planilha. O SharePoint (e o bronze) ficou com o
valor antigo. Três casos não são ajuste:

- 141102024070102 (Ergonomia): a fórmula de `R$ Mês` na linha da planilha 2024 aponta
  para a coluna errada (`$B`/`AH`) e dá 0. O `Ganho mês R$` da linha é 468, igual ao
  bronze.
- 02032025021201: Tempo Ciclo em `mel_ganhos` e `mel_aprovacao`; na planilha a linha
  está sem tipo. O ganho sai das horas (R$ 400,45).
- 26112025021201 (Acondicionamento, R$ 0,20): não está na planilha.

Acondicionamento segue a mesma regra dos demais tipos sem volume (FAO, Manutenção...):
vale o `Ganho mês R$`.

**FAPs aprovadas fora de `mel_aprovacao`.** 348 FAPs "Outros" de 2021 (R$ 342.763) estão
na planilha e não existem em `mel_aprovacao`. No export do SharePoint usado na carga
histórica, 326 delas estão `Aprovado` mas sem nenhuma data (`dt_fap`,
`dt_aprovacao_eng` e linha de ganho vazios), e a carga as separou em
`aprovado_sem_dt_fap`. Outras 9 foram criadas em dez/2020 e ficaram fora do corte de
ano da carga, embora a planilha as lance em 2021. As 13 restantes (R$ 26.698) não estão
em nenhum export. O mesmo acontece com 55 FAPs de TC, Consumo e Troca MP de 2021 e com
19 FAPs "Outros" de ganho 0.

Nos tipos com volume, o corte de ano deixou mais 120 FAPs de 2021 fora (19 TC, 1
Aglutinação, 44 Consumo, 56 Troca MP; R$ 43 mil de MP e 2,8 pessoas na planilha):
aprovadas, criadas em dez/2020 e lançadas na planilha de 2021, com volume já em
`mel_volume_real_hist`. Junto vêm 5 FAPs "Outros" de ganho 0 no mesmo caso. Outras 28
FAPs de MP de 2021 (R$ 85.705) não estão em nenhum export.

Dez FAPs FAO de 2021 (193102021022501 a 509 e 193102021052835) têm mais de uma linha na
planilha com `Ganho mês R$` diferente, um lançamento por posto. O Qlik somava as linhas.

## Decisão

1. **Seed `mel_ganhos_ajuste`** (`numero_fap`, `ganho_previsto`, `referencia` = arquivo e
   linha da planilha), carregado à mão como os demais (ADR 0004). `stg_mel_ganhos` troca
   o `ganho_previsto` do bronze pelo do seed. Entram as 9 FAPs cujo valor certo é o da
   planilha. Os três casos acima ficam com o valor do dbt.
2. **Teste `assert_mel_ganhos_ajuste_valido`**: cada FAP do seed tem uma única linha no
   bronze e tipo sem volume. Com mais linhas, o valor seria somado uma vez por linha; nos
   tipos com volume, `ganho_previsto` não entra no R$.
3. **Carga das FAPs aprovadas que ficaram fora** em `mel_aprovacao`, pelo SQL gerado por
   `dags/melhorias/scripts/aprovacao_planilha.py`: linhas do export com status Aprovado
   que estão na planilha, com `dt_fap` = `Data da FAP` da planilha e tipo da planilha
   quando vazio. FAP anterior a 2025 sem data em nenhuma fonte não entra. São 534 FAPs,
   todas de 2021, em duas cargas: 409 do `aprovado_sem_dt_fap` e das 9 de dez/2020, e
   depois 125 das demais criadas em dez/2020 (`excluidos_mel_aprovacao.csv`, motivo
   `fora_2021_2025`). A cada carga, `ganhos_hist.py` gera de novo `mel_ganhos_hist` com
   essas FAPs na lista (+436 e +1.231 linhas; nenhuma linha anterior muda).
4. **Ganhos diferentes na mesma FAP somam** em `mel_ganhos_hist` (tipos sem volume).
   Linha repetida com o mesmo ganho continua contando uma vez (ADR 0008).
5. As FAPs sem registro em nenhum export são descartadas: 13 "Outros" e 28 de MP.

## Consequências

- O realizado de 2021 ganha as 534 FAPs (Outros pelo `Ganho mês R$`; TC, Aglutinação,
  Consumo e Troca MP pelo volume de `mel_volume_real_hist`, que já tinha o volume delas).
- Corrigir o valor no SharePoint não basta para o dbt mudar: o seed continua mandando.
  Quando o bronze estiver certo, a linha sai do seed.
- `mel_aprovacao` passa a ter linhas que o merge do bronze não conhece (ID antigo, fora
  da janela de 90 dias). O merge só apaga linhas dentro da janela, então elas ficam.

## Alternativas consideradas

- **Corrigir `mel_ganhos` com `update` direto:** o bronze deixa de espelhar o
  SharePoint, e uma edição do item no app desfaz a correção sem aviso.
- **Levar as 409 FAPs só para `mel_ganhos_hist`:** o dbt só conta FAP aprovada em
  `mel_aprovacao` (ADR 0003), e o teste `assert_mel_ganhos_hist_aprovada` barra a carga.
