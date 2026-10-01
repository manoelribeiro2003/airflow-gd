# 0012 — Macro setor nulo preenchido por mapa de setor e zero à esquerda do número da FAP

- Status: aceito
- Data: 2026-09-30
- Issue: #28
- Complementa: [ADR 0006](0006-carga-horaria-macro-setor-corte-qlik.md) (carga horária
  por macro setor) e [ADR 0007](0007-volume-real-historico-planilhas-qlik.md)
  (`mel_volume_real_hist`)

## Contexto

Duas causas de ganho de Tempo Ciclo e Aglutinação zerado no dbt que a reconciliação com
as planilhas do Qlik deixou abertas (`reconciliacao-qlik-2021-2025.md`).

**`macro_setor` nulo.** Antes do corte `volume_hist_ate`, a carga horária sai só de
`mel_carga_horaria_macro`, por (filial, macro_setor, mês) (ADR 0006). Em
`mel_ganhos`, 3.118 linhas têm `macro_setor` nulo, quase todas de Crato entre 2021 e
2024; em `mel_ganhos_hist` são 131. Sem macro setor a linha não acha carga, e o ganho
em pessoas e em R$ fica 0 (warn `assert_ganho_tc_com_carga_horaria`). A planilha
`BASE_LANCAMENTO` tem `Setor Macro` nessas linhas, e a carga desses macros existe.

São 44 pares (filial, setor) com alguma linha sem macro. Em 36 deles o próprio
`mel_ganhos` tem outras linhas do mesmo setor com macro preenchido, e o macro mais usado
ali é o mesmo que o mais usado na planilha, sem exceção. Nos outros 8 só a planilha tem
o macro. Dois setores têm um segundo macro em poucas linhas (`Montagem Cra`: Montagem
em 182 linhas e Laboratório em 2; `Corte For`: Corte em 1.484 e Montagem em 2).

**Zero à esquerda do número da FAP.** Em parte das linhas da planilha a célula de
`Nº F.A.P` está como número, e o Excel tirou o zero inicial: `02032024111401` virou
`2032024111401`. `volume_real_hist.py` gravava a FAP como veio, a linha não casava com
`mel_ganhos.numero_fap` e o volume se perdia. São 6 FAPs (8 linhas); 4 delas, de 2024,
perdiam o volume do offset 2.

O tamanho sozinho não identifica o caso. As planilhas têm células numéricas de 12 e 13
dígitos de FAPs antigas de Crato (`1908210204010`), que são assim mesmo, e o SharePoint
tem FAPs de 13 dígitos (`1172021042704`). Todas as 82 mil FAPs de 14 dígitos do banco
seguem o formato prefixo de 4 dígitos + data `AAAAMMDD` + sequencial de 2.

## Decisão

1. **Seed `mel_macro_setor`** (`filial`, `setor`, `macro_setor`, `origem`), carregado à
   mão como os demais (ADR 0004), com PK (filial, setor). Entram os 44 pares com alguma
   linha sem macro.
2. **Regra do mapa:** o macro mais usado nas linhas de `mel_ganhos` e `mel_ganhos_hist`
   do mesmo (filial, setor) que têm macro (`origem` = `mel_ganhos`); se nenhuma linha
   tem, o `Setor Macro` mais usado na planilha (`origem` = `planilha`).
3. **`stg_mel_ganhos` preenche só o nulo:** `coalesce(macro_setor, <seed>)`, nas duas
   fontes (bronze e hist). O macro cadastrado nunca é trocado.
4. **`fap_key` em `volume_real_hist.py`:** repõe o zero quando a célula é numérica e,
   com o zero, fica no formato da FAP de 14 dígitos. Célula de texto não muda.
   `ganhos_hist.py` usa a mesma função, para a FAP casar com a lista de FAPs do banco.
   `mel_volume_real_hist` é recarregada pelo SQL gerado de novo.

## Consequências

Medido em `fct_ganhos` no build de produção de 2026-09-30, antes e depois (offsets 1 e
2, FAPs aprovadas):

| Ano de `dt_fap` | Pessoas (mapa) | R$ (mapa) | Pessoas (zero da FAP) | R$ (zero da FAP) |
|---|---|---|---|---|
| 2021 | +34,2 | +60.809 | | |
| 2022 | +25,2 | +47.683 | | |
| 2023 | +14,5 | +28.694 | | |
| 2024 | +45,2 | +101.804 | +1,8 | +4.391 |

- 2025 e 2026 não mudam no realizado. O mapa só tem efeito onde o macro era nulo e a
  carga do macro existe: o ganho mudou em 557 FAPs de Crato e uma de Sobral
  (`TS6 - Serigrafia`). Nenhuma linha entrou ou saiu de `fct_ganhos`, e
  `fct_aderencia.atingiu_meta` não mudou.
- O ganho previsto (`int_ganhos_previsto`) das mesmas linhas também deixa de ser 0:
  +R$ 629.556 no quadrimestre, em 618 FAPs de 2021-2024.
- `macro_setor` deixa de ser nulo em 2.211 FAPs de `fct_ganhos`. Sobram 5 linhas de
  `mel_ganhos` sem macro, todas sem setor.
- O warn `assert_ganho_tc_com_carga_horaria` cai de 1.256 para 599 linhas.
- Continua sem carga, porque a carga do macro não existe no período: Crato Compostagem
  (antes de 2025-11), Fortaleza Corte e Frequência (antes de 2025-11), Fortaleza
  Matrizaria e Sobral Área de apoio, entre outros. O warn continua apontando.
- Pré-requisito de deploy: `dbo.mel_macro_setor` existir antes do `dbt build` (a view
  `stg_mel_ganhos` falha sem a tabela).
- Setor novo com macro nulo não entra sozinho no mapa: aparece no warn e ganha uma linha
  no seed. Linha repetida no seed duplicaria o ganho; a PK da tabela e o teste de
  unicidade (fonte, id) de `stg_mel_ganhos` barram.
- Preencher o macro no SharePoint depois não conflita: o cadastro ganha do seed.

## Alternativas consideradas

- **Preencher `macro_setor` na lista do SharePoint:** depende da área para 3 mil linhas
  antigas e não cobre o hist.
- **Derivar o mapa no dbt** (macro mais usado por setor, calculado a cada build): o
  resultado mudaria sozinho com o cadastro, e os 8 setores sem nenhuma linha com macro
  ficariam de fora.
- **Usar o `Setor Macro` da planilha linha a linha:** a planilha não tem chave de linha
  em comum com `mel_ganhos`, e o macro é atributo do setor.
- **Completar o zero só pelo tamanho (13 -> 14):** trocaria FAPs que têm 13 dígitos de
  verdade.
- **Chave alternativa no join de `int_ganhos_calc`**, como em `cod_prod_hist`: evitaria a
  recarga, mas deixaria a tabela com FAP errada e mais um join no model mais pesado.
