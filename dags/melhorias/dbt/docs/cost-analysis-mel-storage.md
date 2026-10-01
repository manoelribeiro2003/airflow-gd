# Análise de custo (bytes/row) — tabelas `mel_` no dbengenharia

- Status: vigente
- Data da medição: 2026-06-18
- Relacionado: [ADR 0001](adr/0001-dbt-views-only-sql-server.md) (views-only),
  [ADR 0005](adr/0005-materializar-caminho-quente-ganhos.md) (materializa caminho quente),
  [performance-threshold.md](performance-threshold.md)

## Objetivo

Estimar quanto disco custa converter os modelos dbt de `melhorias` (hoje todos
VIEW, ver ADR 0001) para tabela materializada, para: (a) saber o espaço mínimo
necessário e o crescimento ao longo do tempo; (b) otimizar as consultas das
`mel_fct_`. O teto do banco é 10 GB (ADR 0001).

## Metodologia

Tamanho lógico real medido direto no banco (SQL Server 2019, dbengenharia), por
objeto com prefixo `mel_`:

```sql
-- por objeto: soma do DATALENGTH real de todas as colunas / contagem de linhas
SELECT COUNT_BIG(*) AS rows,
       SUM(CAST((ISNULL(DATALENGTH([col1]),0) + ISNULL(DATALENGTH([col2]),0) + ...) AS BIGINT)) AS tot
FROM dbo.[<objeto>];
-- bytes/row = tot / rows
```

`DATALENGTH` conta o comprimento real armazenado (varchar real, não o tipo
declarado), então é o tamanho lógico fiel dos dados.

## Medição (2026-06-18)

`BASE TABLE` = seeds/sources, já físicos. `VIEW` = modelo dbt (custo se virar tabela).

| Objeto | Tipo | Rows | B/row | MB lógico |
|---|---|---:|---:|---:|
| mel_int_ganhos_long | VIEW | 339.228 | 135 | 43.84 |
| mel_stg_mel_ganhos | VIEW | 104.223 | 242 | 24.05 |
| mel_int_ganhos_calc | VIEW | 104.223 | 168 | 16.69 |
| mel_fct_ganhos | VIEW | 82.736 | 146 | 11.52 |
| mel_stg_meta_aderencia | VIEW | 43.209 | 189 | 7.79 |
| mel_stg_mel_aprovacao | VIEW | 23.270 | 287 | 6.37 |
| mel_dim_idealizador | VIEW | 43.209 | 108 | 4.43 |
| mel_fct_meta | VIEW | 43.209 | 100 | 4.10 |
| mel_stg_mel_volume_real | VIEW | 22.402 | 37 | 0.80 |
| mel_int_melhorias_realizado | VIEW | 10.474 | 64 | 0.64 |
| mel_fct_aderencia | VIEW | 5.288 | 45 | 0.23 |
| mel_dim_calendario | VIEW | 2.726 | 31 | 0.08 |
| mel_fct_melhorias_em_andamento | VIEW | 425 | 196 | 0.08 |
| demais stg/int/dim pequenos | VIEW | — | — | <0.1 |
| **TOTAL modelos dbt** | | | | **~121 MB lógico** |

Sources físicos (referência): `mel_ganhos` 46 MB, `mel_aprovacao` 32 MB (1.441
B/row, muito varchar de comentário), `mel_meta_aderencia` 9.6 MB,
`mel_volume_real` 0.8 MB.

### Lógico para físico

- Rowstore SQL Server: header de linha + null bitmap + slack de página → fator
  ~1.3. Com 1-2 índices nonclustered → orçar ~1.5.
- **Clustered columnstore (CCI)**: comprime ~5-10×. Tabela materializada com CCI
  fica em ~1/5 a ~1/8 do lógico. dbengenharia é 2019 Standard, suporta CCI.

## Espaço atual do banco (2026-06-18)

Estado real do `dbengenharia` (`sys.database_files` + `FILEPROPERTY`):

| Arquivo | Tipo | Alocado | Usado | Max (teto) | Disponível até o teto |
|---|---|---:|---:|---:|---:|
| dbengenharia | ROWS | 2323.9 MB | 1097.6 MB | 10000 MB | **~8902 MB (~8.7 GB)** |
| dbengenharia_log | LOG | 47.9 MB | 2.1 MB | 2048 MB | ~2000 MB |

O teto de 10 GB do ADR 0001 está configurado de fato como `max_size` do data file.
Hoje o banco usa ~1.1 GB; **sobram ~8.7 GB** até o teto. Edição: SQL Server 2019
Standard. Conclusão: há folga enorme — o caminho quente (~5 MB medido) é ~0.06%
do disponível; mesmo materializar tudo em rowstore (~180 MB) seria ~2%.

## Espaço mínimo

Dois cenários:

| Cenário | Lógico | Físico |
|---|---:|---:|
| Materializar TODOS os modelos como rowstore | ~121 MB | ~180 MB (×1.5 c/ índices) |
| **Caminho quente (4 modelos) com columnstore** — escolhido | ~60 MB | **~10-20 MB** (CCI ~5-8×) |

Modelos do caminho quente: `int_ganhos_long` (43.8), `fct_ganhos` (11.5),
`fct_meta` (4.1), `fct_aderencia` (0.2) = ~59.7 MB lógico → ~10-20 MB com CCI.

**Mínimo prático: ~20 MB.** Mesmo o cenário extremo (~180 MB) cabe folgado nos 10 GB.

## Crescimento

Drivers medidos (rows/ano):

| Driver | rows/ano | Observação |
|---|---:|---|
| mel_ganhos | ~58.000 | 2025=57.6k; 2026 no mesmo ritmo |
| mel_aprovacao | ~15.000 | 2025=13k; 2026 ~17k/ano |
| mel_meta_aderencia | ~86.000 | snapshot ~14.4k × 6 bimestres, **acumula** |
| mel_volume_real | ~17.000 | ~1.4k/mês |

Crescimento físico/ano:

| Cenário | MB/ano |
|---|---:|
| Todos modelos rowstore | ~140 |
| **Caminho quente c/ columnstore** | **~6-8** |

Projeção do caminho quente: praticamente plano — ~20 MB hoje, ~60 MB em 5 anos.
Mesmo o cenário "tudo rowstore" só cruza 1 GB em ~6 anos, sempre dentro dos 10 GB.

### Alerta de longo prazo

`mel_meta_aderencia` / `mel_dim_idealizador` são snapshots por bimestre que
**acumulam** (~86k linhas/ano, ~33 MB/ano lógico — o maior driver de longo
prazo). Não estão no caminho quente, mas se um dia forem materializados, avaliar
retenção (reter só N bimestres) ou particionamento.

## Decisão (ver ADR 0005)

Storage não é o gargalo (cabe nos 10 GB com folga). O gargalo é a recomputação
da subárvore de views (`performance-threshold.md`). Materializar o caminho quente
como **tabela com clustered columnstore**:

- `mel_int_ganhos_long` — corta a recomputação dupla (alimenta `fct_ganhos` e
  `int_melhorias_realizado`/`fct_aderencia`) e o unpivot 4×.
- `mel_fct_ganhos`, `mel_fct_meta`, `mel_fct_aderencia` — extração instantânea no
  refresh do Power BI.

**Tabela, não incremental**: `mel_ganhos` é full-reload do SharePoint com edições
retroativas (`Modified`, `volume_foi_editado`); incremental append silenciaria
edições antigas. Rebuild completo sobre columnstore é sub-segundo no volume atual.

## Resultado medido pós-implementação (2026-06-18)

4 modelos materializados como tabela com clustered columnstore (`dbt run`).

Storage real (`sp_spaceused`, reserved):

| Tabela | Lógico | Físico CCI | Compressão |
|---|---:|---:|---:|
| mel_int_ganhos_long | 43.8 MB | 2.6 MB | ~17× |
| mel_fct_ganhos | 11.5 MB | 1.6 MB | ~7× |
| mel_fct_meta | 4.1 MB | 0.8 MB | ~5× |
| mel_fct_aderencia | 0.2 MB | 0.2 MB | — |
| **Total** | ~60 MB | **~5.3 MB** | |

Footprint real (~5 MB) ficou abaixo do estimado (~10-20 MB).

Velocidade `SELECT *` (view antes → tabela agora):

| Modelo | Antes (view) | Depois (tabela CCI) |
|---|---:|---:|
| mel_fct_aderencia | 3058 ms | 96 ms (32×) — não recomputa int_ganhos_long |
| mel_fct_ganhos | 5268 ms | 2729 ms (~2×) |
| mel_fct_meta | 1388 ms | 1055 ms |
| mel_int_ganhos_long | 12447 ms | 11821 ms (preso na transferência de 339k linhas; ganho = computa 1× por refresh, não 2×) |
