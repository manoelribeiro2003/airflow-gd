# 0007 — Volume real histórico (2021-2025) das planilhas do Qlik

- Status: aceito
- Data: 2026-09-26

## Contexto

O ganho realizado de TC, Aglutinação, Consumo e Troca MP multiplica os componentes da
FAP pelo volume real produzido nos meses após `dt_fap`. No dbt esse volume vem de
`mel_volume_real` (DAG `SILVER_MELHORIAS_VOLUME_REAL`), que só tem dados a partir de
2025-05. Para FAPs de 2021 a 2025-04 o ganho realizado (horas, pessoas, R$) era 0.

O Qlik, fonte oficial de 2021-2025, lia o volume das planilhas
`BASE_LANC_MELHORIAS_<ano>_Sobral.app.*.xlsx`, aba `BASE_LANCAMENTO` (os arquivos
"Sobral" trazem os 3 estabelecimentos). Comparadas com `mel_volume_real` em
2025-05..12, a mediana da razão planilha/DAG é 1,000 nos dois offsets.

Como a planilha organiza o volume:

- arquivo normal: `Data da FAP` = dt_fap, coluna `1º Mês` = volume do mês de dt_fap
  (offset 1);
- arquivo `mês.anterior`: `Data da FAP` = dt_fap + 30 dias, `1º Mês` = volume do mês
  seguinte (offset 2). A coluna `Mês anterior` não é confiável;
- o offset 2 das FAPs de dezembro do ano Y está no `mês.anterior` do ano Y+1;
- 10.876 linhas do `mês.anterior` (2021-11..12 e 2023-01..08) têm `Data da FAP` =
  dt_fap + 60 dias por erro de data; são offset 2;
- dez/2024 aparece em `2024.app.1` e `2025.app.2` (986 volumes divergentes);
- várias linhas por FAP + código (operações/mix) repetem o mesmo volume;
- o Excel guarda o código como número: `0224374` vira `224374`, enquanto
  `mel_ganhos.cod_prod` mantém o zero à esquerda.

## Decisão

1. **Tabela aux `mel_volume_real_hist`** (numero_fap, cod_prod, mes_offset, volume,
   arquivo_origem), PK nas três primeiras, `mes_offset in (1, 2)`. Carga manual
   (ADR 0004) pelo SQL gerado por `dags/melhorias/scripts/volume_real_hist.py` a partir
   das planilhas:
   - offset pelo **nome do arquivo** (normal = 1, `mês.anterior` = 2), nunca pela data;
     isso já cobre dezembro no arquivo do ano seguinte e as linhas com +60 dias;
   - chave em mais de um arquivo: vale o arquivo de ano mais recente (dez/2024 fica com
     `2025.app.2`); volumes diferentes da mesma chave no mesmo arquivo (linha de mix 0
     com volume 0): vale o maior;
   - `cod_prod` gravado sem zeros à esquerda;
   - linha sem FAP, código ou volume numérico é descartada; volume 0 e negativo ficam.
2. **Fonte por mês de competência em `int_ganhos_calc`**, com o mesmo corte do
   histórico Qlik (var `volume_hist_ate`, ADR 0006). Para o mês n da FAP
   (competência = mês de dt_fap + n-1):
   - competência < corte: `mel_volume_real_hist` por `mes_offset = n` e código sem
     zeros à esquerda dos dois lados; se o código exato não casa, tenta o código de
     `mel_ganhos` arredondado por double (`cod_prod_hist_float`): nas planilhas
     2021-2023 os códigos de 16 dígitos acima de 2^53 perderam o último dígito ímpar
     (`...0009` -> `...0008`). Incluído na reconciliação (#21,
     `docs/reconciliacao-qlik-2021-2025.md`);
   - competência >= corte: `mel_volume_real` por `mes_ano`, como antes.

   Corte explícito, sem `coalesce` entre as fontes. O corte é pela competência, não
   por `dt_fap`, porque o offset 2 das FAPs de dez/2025 (jan/2026) não existe na
   planilha e vem de `mel_volume_real`. Para FAPs com dt_fap >= corte, todos os meses
   caem depois do corte, então o resultado não muda.
3. Backfill de `SILVER_MELHORIAS_VOLUME_REAL` não mexe no histórico (tabela separada).

## Consequências

- Pré-requisito de deploy: `dbo.mel_volume_real_hist` existir antes do `dbt build` (a
  view de staging falha sem a tabela).
- Carga atual: 555.864 linhas de 13 planilhas viram 98.767 chaves de offset 1 e 96.209
  de offset 2.
- Validação contra produção (tabelas temporárias de sessão, 2026-09-26): sem
  fan-out (272.776 linhas antes e depois); FAPs com dt_fap >= corte idênticas.
  Horas ganhas por ano de dt_fap (FAPs presentes em `mel_ganhos`) ficam a menos de 3%
  do cálculo direto na planilha em 2021-2025. R$ MP (Consumo + Troca MP) por ano, mesmo
  recorte por FAP:

  | Ano | Horas | R$ MP por FAP | R$ MP por FAP + código em `mel_ganhos` |
  |---|---|---|---|
  | 2021 | -3,0% | -5,8% | 0,0% |
  | 2022 | -0,8% | **-11,9%** | -5,8% |
  | 2023 | -1,0% | -20,6% | -0,1% |
  | 2024 | -1,4% | -0,6% | 0,0% |
  | 2025 | +1,4% | +2,2% | +2,3% |

  O volume por chave bate; o que abre o R$ MP por FAP são componentes (códigos) que
  estão na planilha e não em `mel_ganhos` (issue #20, ADR 0008) e, em 2022, mais linhas de
  operação por componente na planilha do que em `mel_ganhos`. Em 2025 o dbt fica acima
  porque o mês 2 das FAPs de dez/2025 vem de `mel_volume_real` e não existe na planilha.
  Com isso, o critério de ±6% da issue #18 fecha para 2024/2025 e não fecha para R$ MP
  2022 até a #20.
- Offsets 3 e 4 antes do corte ficam 0: a planilha só tem os offsets 1 e 2, e
  `mel_volume_real` também só costuma preencher os dois primeiros meses.
- Mudar o corte é mudar a var; nenhuma data fica fixa nos models.

## Alternativas consideradas

- **Carregar o histórico em `mel_volume_real`**: o backfill da DAG apaga e recalcula
  ranges de `mes_ano`, e o grão é outro (mês calendário, não offset). Tabela separada
  deixa as duas fontes independentes.
- **`coalesce(histórico, volume_real)`**: mistura fontes na mesma FAP sem regra
  explícita e esconde buraco de uma delas.
- **Corte por `dt_fap`**: zeraria o mês 2 das FAPs de dez/2025, que não está na
  planilha.
- **Manter o código como veio da planilha**: 355 linhas de `mel_ganhos` de 2021-2025
  com zero à esquerda no código ficariam sem volume (ex.: uma Troca MP de R$ 100 mil
  em 2022).
