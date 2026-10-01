# ROADMAP — SiMOn OEE por Produto

## Status atual

| Artefato | Status | Descrição |
|---|---|---|
| `sql/tempo_util.sql` | ✅ Pronto | Tempo útil por máquina+produto+dia+turno |
| `sql/disponibilidade.sql` | ✅ Pronto | Paradas com peso por máquina+produto+dia+turno |
| `sql/qualidade.sql` | ✅ Pronto | Perdas de qualidade por máquina+produto+dia+turno |
| `sql/performance_perdas.sql` | ✅ Pronto | Perdas QV/MR por máquina+produto+dia+turno |
| `sql/performance_ciclos.sql` | ✅ Pronto | SaldoTC por máquina+produto+dia+turno |
| `sql/oee_produto.sql` | ✅ Pronto | OEE agregado por produto+dia |
| `IDEIA.md` | ✅ Pronto | Requisitos e fórmulas documentados |

---

## Fase 1 — OEE por Produto (MVP) ✅

**Objetivo:** script SQL que retorna OEE diário por `NumeroProduto` nos últimos 5 dias.

- [x] Documentar requisitos em `IDEIA.md`
- [x] Criar `sql/oee_produto.sql`
  - [x] Parâmetro `@cod_produto_filtro` (NULL = todos, ou lista CSV)
  - [x] Integrar `tempo_util` por produto+dia
  - [x] Integrar `disponibilidade` (Setup + Disponibilidade) por produto+dia
  - [x] Integrar `qualidade` por produto+dia
  - [x] Integrar `performance_perdas` (QV/MR) por produto+dia
  - [x] Integrar `performance_ciclos` (SaldoTC, SQL dinâmico via cursor) por produto+dia
  - [x] Calcular `% OEE`, `% Disp`, `% Perf`, `% Qual`
  - [x] Formatar `tempo_util` e `hrs_boas` como HH:MM:SS

---

## Fase 2 — Robustez e Validação

**Objetivo:** garantir que os números batem com o Power BI (SiMOn 2.0).

- [ ] Validar output de `oee_produto.sql` contra dashboard Power BI por produto/data conhecido
- [ ] Identificar e corrigir discrepâncias de lógica de turno (horários especiais por setor)
- [ ] Adicionar coluna `pct_setup` separada no output (atualmente agrupada em `pct_disp`)
- [ ] Testar produtos que rodam em múltiplas máquinas simultaneamente
- [ ] Testar produto com `DataFim IS NULL` (produto ainda em produção)
- [ ] Documentar bug corrigido: filtro `cod_motivo_parada = 826` em `disponibilidade.sql` era de debug

---

## Fase 3 — Encapsulamento (Stored Procedure)

**Objetivo:** transformar o script em objeto reutilizável no banco.

- [ ] Criar `sp_oee_produto` com parâmetros:
  - `@cod_produto_filtro NVARCHAR(MAX) = NULL`
  - `@DataInicioAnalise  DATETIME = NULL` (default: GETDATE()-5)
  - `@DataFimAnalise     DATETIME = NULL` (default: GETDATE())
- [ ] Documentar uso da procedure
- [ ] Testar call sem parâmetros (retorna todos os produtos dos últimos 5 dias)

---

## Fase 4 — Integração Python / Aplicação

**Objetivo:** consumir `oee_produto` via Python para automação ou dashboard alternativo.

- [ ] Criar cliente Python com `pyodbc`
- [ ] Expor como endpoint REST ou exportar para CSV/Excel
- [ ] Definir TTL de cache (dados dos últimos 5 dias mudam com frequência)
- [ ] Mapear `NumeroProduto` para descrição de produto (tabela auxiliar a identificar)

---

## Fase 5 — Expansão de Escopo

**Objetivo:** ampliar a análise para outros agrupamentos.

- [ ] OEE por `Setor` (ID_Pavilhao) por dia
- [ ] OEE por `Máquina` por dia (SQLs base já têm granularidade; só agregar diferente)
- [ ] OEE consolidado por `Fábrica` por semana/mês
- [ ] Alertas: produto com OEE abaixo de threshold nos últimos N dias

---

## Decisões técnicas registradas

| Decisão | Motivo |
|---|---|
| Script em vez de VIEW | SQL Server 2008 não suporta VIEW com SQL dinâmico (CURSOR/EXEC) |
| CURSOR para tabelas `Ciclo X` | Número de máquinas varia; INFORMATION_SCHEMA descobre em runtime |
| `CHARINDEX` para filtro CSV | `STRING_SPLIT` disponível apenas a partir do SQL Server 2016 |
| `WITH (NOLOCK)` em todas as tabelas | Padrão do projeto — banco de produção com alto volume de escrita |
| Filtros `ID_Pavilhao NOT IN (...)` | Setores excluídos do OEE conforme configuração SiMOn |
