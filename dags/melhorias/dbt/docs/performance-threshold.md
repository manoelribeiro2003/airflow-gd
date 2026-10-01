# Threshold de performance — views melhorias (dbt)

- Status: vigente
- Data da medição: 2026-06-03
- Relacionado: [ADR 0001](adr/0001-dbt-views-only-sql-server.md) (tudo materializado como VIEW)

## Ambiente

- **SGBD**: Microsoft SQL Server **2019** (RTM-CU18, KB5017593) 15.0.4261.1 (X64),
  **Standard Edition**, Windows Server 2019.
  - 2019 Standard tem **batch mode on rowstore** e **columnstore index** — escala
    melhor que a suposição inicial de SQL 2008.
  - Nota: o `openssl.cnf` (TLS downgrade) e o `msodbcsql17` no `Dockerfile` NÃO são
    pra este banco — servem os **fontes 2008 R2** (`elipse`/`sob`/`for`/`cra`),
    que exigem TLS antigo. `dbengenharia` é 2019.
- Materialização: **VIEW** para todos os models (staging/intermediate/marts), em
  `dbengenharia.dbo`, prefixo `mel_`. Consumo: Power BI **import**.

## Achado central

**O custo NÃO escala pela linha do fato — escala pela recomputação da subárvore.**
Como todo model é VIEW, cada consumidor re-executa a árvore inteira abaixo dele.

Prova: `mel_fct_aderencia` tem só **5.288 linhas** mas leva **~3s** no `SELECT *`,
porque por baixo re-executa `int_ganhos_long → int_melhorias_realizado`.

Gargalo único = **`mel_int_ganhos_long`**:

1. **4× UNION ALL** (unpivot meses 1..4): explode 102k → **333k linhas**.
2. **2 joins de string forçados a `COLLATE DATABASE_DEFAULT`** (carga/custo) → mata
   index seek, vira scan/hash. Hoje barato (dims de 2.204 / 396 linhas).
3. **Consumida 2× num refresh**: por `fct_ganhos` E por `int_melhorias_realizado`
   (que alimenta `fct_aderencia`). Refresh completo roda essa subárvore no mínimo
   duas vezes.

## Números medidos (2026-06-03)

Tabelas-fonte:

| Tabela | Linhas |
|---|---|
| `mel_ganhos` (driver principal) | 102.376 |
| `mel_aprovacao` | 22.714 |
| `mel_meta_aderencia` | 43.209 |
| `mel_carga_horaria` | 2.204 |
| `mel_custo_funcionario` | 396 |

Tempo de execução das views (`count(*)` força o GROUP BY; `SELECT *` = o que o
Power BI import roda de verdade, com cálculo de coluna + rede ao container):

| View | Linhas saída | count(*) | SELECT * |
|---|---|---|---|
| `mel_stg_mel_ganhos` | 102.376 | 83ms | — |
| `mel_int_ganhos_calc` | 102.376 | 88ms | — |
| **`mel_int_ganhos_long`** | **333.840** | 854ms | **12.447ms** |
| **`mel_fct_ganhos`** | 80.852 | 1.903ms | **5.268ms** |
| `mel_int_melhorias_realizado` | 10.302 | 529ms | — |
| **`mel_fct_aderencia`** | **5.288** | 36ms | **3.058ms** |
| `mel_fct_meta` | 43.209 | 31ms | 1.388ms |
| `mel_fct_melhorias_em_andamento` | 2.554 | 40ms | 40ms |

Refresh completo hoje ≈ 10-12s sequencial. **Tranquilo, folga grande.**

## Threshold — a partir de quando se preocupar

Driver = linhas em **`mel_ganhos`** (cada uma vira 4 no unpivot). GROUP BY sobre
linhas largas (13 chaves) escala ~`n log n`.

| `mel_ganhos` | Unpivot | Cenário | Ação |
|---|---|---|---|
| ~100k (hoje) | 333k | `fct_ganhos` ~5s, refresh ~10s | **Nada.** |
| **~250-400k** | ~1-1,5M | `int_ganhos_long` dezenas de s; refresh em minutos | **Atenção** — materializar caminho quente |
| > ~500k | > 1,5M | recomputação múltipla estoura timeout de gateway | **Materializar** `int_ganhos_long` como tabela |

**Regra prática: começar a se preocupar perto de ~250-300k linhas em `mel_ganhos`**
(~3× o atual). Antes disso, view está OK.

## O que fazer ao chegar lá (ordem custo/benefício)

1. **`int_ganhos_long` → `+materialized: table`** (ou incremental por bimestre).
   Maior ganho: corta a dupla recomputação e o unpivot repetido. Não fere o limite
   de 10GB (333k × 15 colunas é trivial; o teto é storage do Power BI, não da view).
2. **Eliminar o `COLLATE DATABASE_DEFAULT`** nos joins de `carga_horaria` /
   `custo_funcionario`: normalizar collation na origem permite seek se a base crescer.
3. **Columnstore**: 2019 Standard suporta. Em `int_ganhos_long` materializado como
   tabela, um nonclustered columnstore acelera o GROUP BY do `fct_ganhos` via batch mode.
4. Só então olhar `fct_ganhos` / `fct_aderencia` — baratos assim que a base vira tabela.

## Como reproduzir a medição

Dentro do container (credencial via Airflow Variable, nunca exposta):

```python
import time
from sqlalchemy import text
from global_modules.database import get_eng_conn

with get_eng_conn().connect() as conn:
    for v in ["mel_fct_ganhos", "mel_fct_aderencia", "mel_int_ganhos_long"]:
        t0 = time.perf_counter()
        rows = conn.execute(text(f"select * from dbo.{v}")).fetchall()
        print(v, len(rows), f"{(time.perf_counter()-t0)*1000:.0f}ms")
```

```bash
docker exec -w /opt/airflow/dags airflow-airflow-worker-1 python <script>.py
```
