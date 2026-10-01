# 0010 — TC/Aglutinação em setor Ting% não soma troca MP

- Status: aceito
- Data: 2026-09-29
- Issue: #26
- Complementa: [ADR 0003](0003-contrato-gold-ganhos-long-dt-fap-aprovadas.md) (regra de
  ganho por tipo)

## Contexto

O Qlik (`load_data_for_dashboard`) calcula `ganho troca MP 1..4` para qualquer tipo
quando `Setor like 'Ting*'`, e a medida do painel (`docs/qlik/ganho_melhorias.md`)
soma `[ganho em reais 1] + [ganho consumo 1] + [ganho mês outras melhorias]`, com
`[ganho consumo 1] = [g consumo 1] + [ganho troca MP 1]`. Uma FAP de Tempo Ciclo ou
Aglutinação de Tingimento entrava no painel com as horas convertidas em R$ **e** o
delta de custo par.

A planilha `BASE_LANCAMENTO` não faz isso: `R$ Mês` de TC/Aglutinação é só a coluna
das horas (`CX`), em qualquer setor. O dbt seguia a planilha no R$
(`ganho_reais_case` pega o ramo TC/Aglut primeiro), mas `int_ganhos_calc` ainda
calculava `troca_mp_1..4` para essas FAPs, e o valor ficava sem uso.

Medido em 2026-09-29 (prod e planilhas 2021):

- 41 FAPs aprovadas de TC/Aglutinação em setor Ting%, todas de 2021 (Tingimento F7).
  `troca_mp` mês 1 R$ 2.575, quadrimestre R$ 5.614.
- Nas planilhas, as 41 têm `Custo Par Anterior/Atual` preenchido, `Ganho mês R$`
  vazio e `R$ Mês` = horas.
- Por FAP, `troca_mp_1` fica entre 0,88 e 1,01 vezes o R$ das horas
  (`hrs_ganhas_1 / ch_mensal * custo`); 32 das 41 ficam a menos de 2%. O custo par
  cadastrado nessas FAPs é o custo de mão de obra por par: o delta mede o mesmo ganho
  de tempo de ciclo, só que por outro caminho.

## Decisão

1. **A referência é a planilha.** TC/Aglutinação de Ting% vale só as horas
   convertidas em R$. Somar `troca_mp` contaria o mesmo ganho duas vezes, e o painel
   Qlik fazia isso nessas 41 FAPs.
2. **`troca_mp` só para Consumo e Troca de Matéria Prima.** `int_ganhos_calc` calcula
   `troca_mp{_previsto}_1..4` quando `tipo = 'Troca de Matéria Prima'` ou
   `tipo = 'Consumo' and setor like 'Ting%'` (a regra Qlik de Consumo em Tingimento
   continua). Os demais tipos ficam com 0, inclusive os tipos sem volume de Ting%, que
   usam o `ganho_previsto` (issue #23).
3. **Teste** `assert_troca_mp_so_consumo_troca`: falha se algum tipo fora de Consumo
   e Troca MP tiver `troca_mp` diferente de 0.

## Consequências

- `fct_ganhos`, `int_ganhos_previsto` e as marts não mudam: `ganho_reais_case` já
  ignorava `troca_mp` fora de Consumo/Troca MP. A mudança é só em `int_ganhos_calc`.
- Quem comparar com o painel Qlik vai ver essas FAPs de 2021 abaixo do Qlik, na
  diferença de `troca_mp` do mês 1 (R$ 2.575 no ano).

## Alternativas consideradas

- **Seguir o Qlik** (somar `troca_mp` do mês 1 no ramo TC/Aglut): repete o ganho das
  horas, diverge da planilha que a área usava para lançar e obrigaria uma exceção
  "só mês 1" na macro.
- **Manter o cálculo sem uso**: deixa um valor em R$ no model que ninguém soma e que
  convida a somar de novo.
