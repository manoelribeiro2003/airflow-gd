# Objetivo
Calcular o OEE por `NumeroProduto` dos últimos 5 dias (`GETDATE() - 5`), agregado por dia.

## Fórmulas OEE
Referências: `OEE.DAX.md` e `OEE.md`

```
% Disp  = Σ paradas_com_peso (família ≠ Setup) / Σ tempo_util
% Setup = Σ paradas_com_peso (família = Setup)  / Σ tempo_util
% Perf  = Σ (SaldoTC + perdas_QV_MR)           / Σ tempo_util
% Qual  = Σ tempo_apontamento_qualidade          / Σ tempo_util

OEE = 1 - %Disp - %Setup - %Perf - %Qual

Hrs Boas (s) = tempo_util × OEE   ← tempo efetivamente produtivo
```

> `% Disp` no output agrupa Disponibilidade + Setup para simplificar a leitura.

## Fontes de dados (sql/)

| Arquivo | Tabelas-chave | Dado gerado |
|---|---|---|
| `tempo_util.sql` | Produtos, Paradas (sem peso), Horarios | `tempo_util` em segundos |
| `disponibilidade.sql` | Paradas (com peso), Familia_paradas | `tempo_parada` por família (Setup / Disponibilidade) |
| `qualidade.sql` | Perdas_Qualidade | `tempo_apontamento` em segundos |
| `performance_perdas.sql` | Perdas_Performance | `tempo_perda` QV/MR em segundos |
| `performance_ciclos.sql` | `Ciclo <ID>` (tabela por máquina) | `soma_ganho_ciclo`, `soma_perda_ciclo` → SaldoTC |

## Requisitos

- OEE calculado por `NumeroProduto` + dia, últimos 5 dias.
- Um produto pode rodar em várias máquinas; somar tudo por produto+dia.
- Tabelas ciclo: `Ciclo <ID_Maquina>` — descoberta dinâmica via `INFORMATION_SCHEMA`.

## Uso

```sql
-- Alterar @cod_produto_filtro no topo do script:
DECLARE @cod_produto_filtro NVARCHAR(MAX) = NULL;          -- todos
DECLARE @cod_produto_filtro NVARCHAR(MAX) = '25122';       -- um produto
DECLARE @cod_produto_filtro NVARCHAR(MAX) = '25122,06466'; -- múltiplos (sem espaços)
```

> **Limitação SQL Server 2008:** VIEW não suporta SQL dinâmico.
> `oee_produto` é implementado como script (`sql/oee_produto.sql`), não como VIEW.

## Saída esperada

| Produto | % OEE | Tempo útil | Hrs Boas | % Disp | % Perf | % Qual | Data |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1931602 - CABEDAL INJ GRENDHA... | 51,05% | 20:24:48 | 10:26:32 | 29,50% | 14,30% | 5,15% | 08/05/2026 |

> Valores de exemplo acima são ilustrativos.

## Stack

- SQL Server 2008 (banco `elipse`, usuário read-only)
- Driver: ODBC Driver 17 for SQL Server

