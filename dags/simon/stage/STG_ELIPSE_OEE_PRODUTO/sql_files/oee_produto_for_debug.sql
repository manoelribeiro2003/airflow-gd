-- =============================================================================
-- oee_produto_for_debug.sql
-- OEE diário por NumeroProduto — versão DEBUG com temp tables para DBeaver
--
-- Cada passo é materializado em uma temp table.
-- Execute o script inteiro ou selecione blocos individuais para inspecionar.
-- Linhas ► DEBUG podem ser descomentadas para ver cada etapa isoladamente.
--
-- Fórmula:
--   OEE = 1 - (tempo_disp + tempo_setup + saldo_tc + tempo_perf_perdas + tempo_qual) / tempo_util
--
-- Pipeline de temp tables:
--   #ciclos → #horarios → #turnos_grid → #produtos_validos
--   → #paradas_sem_peso → #prod_parada_sp
--   → #agg_calendario + #agg_sem_peso → #tempo_util
--   → #familias → #paradas_com_peso → #disp
--   → #qual + #perf_perdas + #saldo_tc
--   → #oee → SELECT final
-- =============================================================================

-- ============================================================
-- PARÂMETROS — ajuste aqui antes de executar
-- ============================================================
DECLARE @DataInicioAnalise  DATETIME      = GETDATE() - 5;
DECLARE @DataFimAnalise     DATETIME      = GETDATE();
DECLARE @cod_produto_filtro NVARCHAR(MAX) = NULL; -- NULL = todos | '25122' = um | '25122,06466' = múltiplos (sem espaços)

-- ===========================================================================
-- ETAPA 1: #ciclos — SaldoTC dos ciclos (SQL dinâmico via CURSOR)
-- ===========================================================================
IF OBJECT_ID('tempdb..#ciclos') IS NOT NULL DROP TABLE #ciclos;

CREATE TABLE #ciclos (
    cod_produto  NVARCHAR(50) COLLATE DATABASE_DEFAULT NOT NULL,
    data_ciclo   DATE                                  NOT NULL,
    soma_ganho   FLOAT                                 NOT NULL,
    soma_perda   FLOAT                                 NOT NULL
);

DECLARE @sql_union  NVARCHAR(MAX) = '';
DECLARE @tableName  NVARCHAR(255);
DECLARE @ID_Maq     NVARCHAR(10);
DECLARE @dtIni      NVARCHAR(30)  = CAST(@DataInicioAnalise AS NVARCHAR(30));
DECLARE @dtFim      NVARCHAR(30)  = CAST(@DataFimAnalise    AS NVARCHAR(30));
DECLARE @dtIniDate  NVARCHAR(20)  = CAST(CAST(@DataInicioAnalise AS DATE) AS NVARCHAR(20));
DECLARE @dtFimDate  NVARCHAR(20)  = CAST(CAST(@DataFimAnalise    AS DATE) AS NVARCHAR(20));

DECLARE ciclo_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT TABLE_NAME
    FROM [Elipse].INFORMATION_SCHEMA.TABLES WITH (NOLOCK)
    WHERE TABLE_NAME LIKE 'Ciclo %'
      AND TABLE_NAME NOT IN ('Ciclo 0', 'Ciclo_Plastisol')
      AND TABLE_TYPE = 'BASE TABLE';

OPEN ciclo_cursor;
FETCH NEXT FROM ciclo_cursor INTO @tableName;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @ID_Maq = SUBSTRING(@tableName, 7, LEN(@tableName) - 6);

    IF LEN(@sql_union) > 0
        SET @sql_union = @sql_union + ' UNION ALL ';

    SET @sql_union = @sql_union +
        'SELECT
            ' + @ID_Maq + '      AS cod_maquina,
            E3TimeStamp          AS ts_ciclo,
            NumeroProduto        AS cod_produto,
            CASE WHEN Diferenca <= 0 THEN Diferenca ELSE 0 END AS ganho_ciclo,
            CASE WHEN Diferenca >= 0 THEN Diferenca ELSE 0 END AS perda_ciclo
        FROM [Elipse].dbo.' + QUOTENAME(@tableName) + ' WITH(NOLOCK)
        WHERE E3TimeStamp >= ''' + @dtIni + '''
          AND E3TimeStamp <= ''' + @dtFim + '''';

    FETCH NEXT FROM ciclo_cursor INTO @tableName;
END

CLOSE ciclo_cursor;
DEALLOCATE ciclo_cursor;

IF LEN(@sql_union) > 0
BEGIN
    DECLARE @sql_insert_ciclos NVARCHAR(MAX) = N'
        INSERT INTO #ciclos (cod_produto, data_ciclo, soma_ganho, soma_perda)
        SELECT
            c.cod_produto,
            CAST(
                CASE
                    WHEN CAST(c.ts_ciclo AS TIME) < hor.Ini_1_T1
                    THEN DATEADD(DAY, -1, c.ts_ciclo)
                    ELSE c.ts_ciclo
                END AS DATE
            ) AS data_ciclo,
            SUM(c.ganho_ciclo) AS soma_ganho,
            SUM(c.perda_ciclo) AS soma_perda
        FROM (' + @sql_union + ') AS c
        LEFT JOIN Maquinas         m   WITH(NOLOCK) ON m.ID       = c.cod_maquina
        LEFT JOIN Pavilhao         pav WITH(NOLOCK) ON pav.ID     = m.ID_Pavilhao
        LEFT JOIN Parametros_Setor ps  WITH(NOLOCK) ON ps.Setor   = pav.Pavilhao
        LEFT JOIN Horarios         hor WITH(NOLOCK) ON hor.Nome   = ps.Horario
        WHERE pav.ID          NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
          AND pav.ID_Fabrica  NOT IN (38, 43)
          AND CAST(
                CASE
                    WHEN CAST(c.ts_ciclo AS TIME) < hor.Ini_1_T1
                    THEN DATEADD(DAY, -1, c.ts_ciclo)
                    ELSE c.ts_ciclo
                END AS DATE
              ) BETWEEN ''' + @dtIniDate + ''' AND ''' + @dtFimDate + '''
        GROUP BY
            c.cod_produto,
            CAST(
                CASE
                    WHEN CAST(c.ts_ciclo AS TIME) < hor.Ini_1_T1
                    THEN DATEADD(DAY, -1, c.ts_ciclo)
                    ELSE c.ts_ciclo
                END AS DATE
            )';

    EXEC sp_executesql @sql_insert_ciclos;
END;

-- ► DEBUG: SELECT COUNT(*) AS cnt_ciclos FROM #ciclos;
-- ► DEBUG: SELECT TOP 100 * FROM #ciclos ORDER BY data_ciclo DESC;

-- ===========================================================================
-- ETAPA 2: Passos materializados em temp tables
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Passo 1 — #horarios: horários por setor
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#horarios') IS NOT NULL DROP TABLE #horarios;

SELECT
    pav.ID        AS cod_setor,
    hor.Ini_1_T1, hor.Fim_1_T1,
    hor.Ini_1_T2, hor.Fim_1_T2,
    hor.Ini_1_T3, hor.Fim_1_T3
INTO #horarios
FROM Pavilhao          pav WITH(NOLOCK)
LEFT JOIN Parametros_Setor ps  WITH(NOLOCK) ON ps.Setor  = pav.Pavilhao
LEFT JOIN Horarios         hor WITH(NOLOCK) ON hor.Nome  = ps.Horario
WHERE pav.ID NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62);

-- ► DEBUG: SELECT COUNT(*) AS cnt_horarios FROM #horarios;
-- ► DEBUG: SELECT * FROM #horarios;

-- ---------------------------------------------------------------------------
-- Passo 2 — #turnos_grid: grade de turnos por setor+dia
--           (DatasParaAnalisar permanece como CTE recursiva inline)
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#turnos_grid') IS NOT NULL DROP TABLE #turnos_grid;

;WITH DatasParaAnalisar AS (
    SELECT CAST(DATEADD(DAY, -1, @DataInicioAnalise) AS DATE) AS Dia
    UNION ALL
    SELECT DATEADD(DAY, 1, Dia)
    FROM DatasParaAnalisar
    WHERE Dia < CAST(@DataFimAnalise AS DATE)
)
SELECT *
INTO #turnos_grid
FROM (
    -- Turno 1
    SELECT
        h.cod_setor, d.Dia AS data_turno, 1 AS num_turno,
        CAST(CAST(d.Dia AS VARCHAR) + ' ' + CAST(h.Ini_1_T1 AS VARCHAR) AS DATETIME) AS inicio_turno,
        CAST(CAST(d.Dia AS VARCHAR) + ' ' + CAST(h.Fim_1_T1 AS VARCHAR) AS DATETIME) AS fim_turno
    FROM DatasParaAnalisar d CROSS JOIN #horarios h
    UNION ALL
    -- Turno 2
    SELECT
        h.cod_setor, d.Dia, 2,
        CAST(CAST(CASE WHEN CAST(h.Ini_1_T2 AS TIME) < CAST(h.Ini_1_T1 AS TIME)
                       THEN DATEADD(DAY, 1, d.Dia) ELSE d.Dia END AS VARCHAR)
             + ' ' + CAST(h.Ini_1_T2 AS VARCHAR) AS DATETIME),
        CAST(CAST(CASE WHEN CAST(h.Fim_1_T2 AS TIME) < CAST(h.Ini_1_T1 AS TIME)
                       THEN DATEADD(DAY, 1, d.Dia) ELSE d.Dia END AS VARCHAR)
             + ' ' + CAST(h.Fim_1_T2 AS VARCHAR) AS DATETIME)
    FROM DatasParaAnalisar d CROSS JOIN #horarios h
    UNION ALL
    -- Turno 3
    SELECT
        h.cod_setor, d.Dia, 3,
        CAST(CAST(CASE WHEN h.Ini_1_T3 = '00:57:01'
                            OR CAST(h.Ini_1_T3 AS TIME) < CAST(h.Ini_1_T1 AS TIME)
                       THEN DATEADD(DAY, 1, d.Dia) ELSE d.Dia END AS VARCHAR)
             + ' ' + CAST(h.Ini_1_T3 AS VARCHAR) AS DATETIME),
        CAST(CAST(CASE WHEN CAST(h.Fim_1_T3 AS TIME) < CAST(h.Ini_1_T3 AS TIME)
                            OR h.Ini_1_T3 = '00:57:01'
                       THEN DATEADD(DAY, 1, d.Dia) ELSE d.Dia END AS VARCHAR)
             + ' ' + CAST(h.Fim_1_T3 AS VARCHAR) AS DATETIME)
    FROM DatasParaAnalisar d CROSS JOIN #horarios h
) AS t
OPTION (MAXRECURSION 0);

-- ► DEBUG: SELECT COUNT(*) AS cnt_turnos FROM #turnos_grid;
-- ► DEBUG: SELECT TOP 50 * FROM #turnos_grid ORDER BY data_turno, cod_setor, num_turno;

-- ---------------------------------------------------------------------------
-- Passo 3 — #produtos_validos: produtos ativos no período (sem duplicatas)
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#produtos_validos') IS NOT NULL DROP TABLE #produtos_validos;

SELECT
    prod.ID_Maq,
    maq.ID_Pavilhao AS cod_setor,
    prod.NumeroProduto AS cod_produto,
    prod.DataInicio,
    COALESCE(prod.DataFim, GETDATE()) AS DataFim,
    prod.DataFim AS DataFim_Original
INTO #produtos_validos
FROM Produtos  prod WITH(NOLOCK)
LEFT JOIN Maquinas maq WITH(NOLOCK) ON maq.ID       = prod.ID_Maq
LEFT JOIN Pavilhao pav WITH(NOLOCK) ON pav.ID       = maq.ID_Pavilhao
WHERE prod.DataInicio                    <= @DataFimAnalise
  AND COALESCE(prod.DataFim, GETDATE())  >= @DataInicioAnalise
  AND maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
  AND pav.ID_Fabrica  NOT IN (38, 43)
  AND prod.ID NOT IN (
      SELECT p2.ID
      FROM Produtos p2 WITH(NOLOCK)
      JOIN (
          SELECT ID_Maq, NumeroProduto,
                 CAST(DataInicio AS DATETIME2(0)) AS DataInicioAgrupada
          FROM Produtos WITH(NOLOCK)
          GROUP BY ID_Maq, NumeroProduto, CAST(DataInicio AS DATETIME2(0))
          HAVING COUNT(*) > 1
      ) dup ON p2.ID_Maq = dup.ID_Maq
           AND p2.NumeroProduto = dup.NumeroProduto
           AND CAST(p2.DataInicio AS DATETIME2(0)) = dup.DataInicioAgrupada
      WHERE p2.DataFim IS NULL
  );

-- ► DEBUG: SELECT COUNT(*) AS cnt_produtos FROM #produtos_validos;
-- ► DEBUG: SELECT TOP 50 * FROM #produtos_validos ORDER BY DataInicio DESC;

-- ---------------------------------------------------------------------------
-- Passo 4 — #paradas_sem_peso: paradas sem peso no período
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#paradas_sem_peso') IS NOT NULL DROP TABLE #paradas_sem_peso;

SELECT par.*
INTO #paradas_sem_peso
FROM Paradas        par WITH(NOLOCK)
LEFT JOIN Motivo_Paradas mp WITH(NOLOCK) ON mp.Codigo = par.Codigo
WHERE mp.PesoOEE     = 'Sem Peso'
  AND par.Hora_Inicio <= @DataFimAnalise
  AND par.E3TimeStamp >= @DataInicioAnalise;

-- ► DEBUG: SELECT COUNT(*) AS cnt_paradas_sp FROM #paradas_sem_peso;
-- ► DEBUG: SELECT TOP 50 * FROM #paradas_sem_peso ORDER BY Hora_Inicio DESC;

-- ---------------------------------------------------------------------------
-- Passo 5 — #prod_parada_sp: interseção produto × parada sem peso
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#prod_parada_sp') IS NOT NULL DROP TABLE #prod_parada_sp;

SELECT
    prod.ID_Maq, prod.cod_setor, prod.cod_produto,
    prod.DataInicio, prod.DataFim,
    CASE WHEN par.Hora_Inicio < prod.DataInicio THEN prod.DataInicio ELSE par.Hora_Inicio END AS ini_parada,
    CASE WHEN par.E3TimeStamp > prod.DataFim    THEN prod.DataFim    ELSE par.E3TimeStamp END AS fim_parada
INTO #prod_parada_sp
FROM #produtos_validos prod
LEFT JOIN #paradas_sem_peso par
    ON par.Maquina_ID  = prod.ID_Maq
   AND par.Hora_Inicio <= prod.DataFim
   AND par.E3TimeStamp >= prod.DataInicio;

-- ► DEBUG: SELECT COUNT(*) AS cnt_prod_parada_sp FROM #prod_parada_sp;
-- ► DEBUG: SELECT TOP 50 * FROM #prod_parada_sp WHERE ini_parada IS NOT NULL ORDER BY ini_parada DESC;

-- ---------------------------------------------------------------------------
-- Passo 6 — #agg_calendario: tempo calendário por produto+turno
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#agg_calendario') IS NOT NULL DROP TABLE #agg_calendario;

SELECT
    p.cod_produto,
    t.data_turno,
    t.num_turno,
    t.cod_setor,
    SUM(DATEDIFF(SECOND,
        CASE WHEN p.DataInicio > t.inicio_turno THEN p.DataInicio ELSE t.inicio_turno END,
        CASE WHEN p.DataFim    < t.fim_turno    THEN p.DataFim    ELSE t.fim_turno    END
    )) AS tempo_calendario
INTO #agg_calendario
FROM #produtos_validos p
JOIN #turnos_grid t
    ON p.DataInicio < t.fim_turno
   AND p.DataFim    > t.inicio_turno
   AND p.cod_setor  = t.cod_setor
GROUP BY p.cod_produto, t.data_turno, t.cod_setor, t.num_turno;

-- ► DEBUG: SELECT COUNT(*) AS cnt_agg_calendario FROM #agg_calendario;
-- ► DEBUG: SELECT TOP 50 * FROM #agg_calendario ORDER BY data_turno DESC;

-- ---------------------------------------------------------------------------
-- Passo 7 — #agg_sem_peso: tempo sem peso por produto+turno
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#agg_sem_peso') IS NOT NULL DROP TABLE #agg_sem_peso;

SELECT
    p.cod_produto,
    t.data_turno,
    t.num_turno,
    t.cod_setor,
    SUM(DATEDIFF(SECOND,
        CASE WHEN p.ini_parada > t.inicio_turno THEN p.ini_parada ELSE t.inicio_turno END,
        CASE WHEN p.fim_parada < t.fim_turno    THEN p.fim_parada ELSE t.fim_turno    END
    )) AS tempo_sem_peso
INTO #agg_sem_peso
FROM #prod_parada_sp p
JOIN #turnos_grid t
    ON p.ini_parada < t.fim_turno
   AND p.fim_parada > t.inicio_turno
   AND p.cod_setor  = t.cod_setor
GROUP BY p.cod_produto, t.data_turno, t.cod_setor, t.num_turno;

-- ► DEBUG: SELECT COUNT(*) AS cnt_agg_sem_peso FROM #agg_sem_peso;
-- ► DEBUG: SELECT TOP 50 * FROM #agg_sem_peso ORDER BY data_turno DESC;

-- ---------------------------------------------------------------------------
-- Passo 8 — #tempo_util: tempo útil por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#tempo_util') IS NOT NULL DROP TABLE #tempo_util;

SELECT
    cal.cod_produto,
    cal.data_turno AS data,
    SUM(cal.tempo_calendario) AS tempo_calendario,
    SUM(COALESCE(sp.tempo_sem_peso, 0)) AS tempo_sem_peso,
    SUM(
        CASE
            WHEN COALESCE(sp.tempo_sem_peso, 0) > cal.tempo_calendario THEN 0
            ELSE cal.tempo_calendario - COALESCE(sp.tempo_sem_peso, 0)
        END
    ) AS tempo_util
INTO #tempo_util
FROM #agg_calendario cal
LEFT JOIN #agg_sem_peso sp
    ON sp.cod_produto = cal.cod_produto
   AND sp.data_turno  = cal.data_turno
   AND sp.num_turno   = cal.num_turno
   AND sp.cod_setor   = cal.cod_setor
WHERE cal.data_turno >= CAST(@DataInicioAnalise AS DATE)
GROUP BY cal.cod_produto, cal.data_turno;

-- ► DEBUG: SELECT COUNT(*) AS cnt_tempo_util FROM #tempo_util;
-- ► DEBUG: SELECT TOP 50 * FROM #tempo_util ORDER BY data DESC;

-- ---------------------------------------------------------------------------
-- Passo 9 — #familias: mapeamento família → grupo OEE
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#familias') IS NOT NULL DROP TABLE #familias;

SELECT
    ID AS cod_familia,
    CASE
        WHEN ID IN (65, 116, 139)                                        THEN 2  -- Manutenção
        WHEN ID IN (66, 115)                                             THEN 3  -- Matrizaria
        WHEN ID IN (67,70,73,76,78,79,80,81,82,83,84,87,
                    119,120,121,122,137,138)                             THEN 1  -- Produção
        WHEN ID = 71                                                     THEN 4  -- Tingimento
        WHEN ID = 86                                                     THEN 5  -- Setup
        ELSE NULL
    END AS cod_agg_familia
INTO #familias
FROM Familia_paradas WITH(NOLOCK);

-- ► DEBUG: SELECT * FROM #familias ORDER BY cod_agg_familia;

-- ---------------------------------------------------------------------------
-- Passo 10 — #paradas_com_peso: paradas COM PESO no período
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#paradas_com_peso') IS NOT NULL DROP TABLE #paradas_com_peso;

SELECT
    par.Maquina_ID,
    par.NumeroProduto  AS cod_produto,
    par.Hora_Inicio    AS ts_inicio,
    par.E3TimeStamp    AS ts_fim,
    maq.ID_Pavilhao    AS cod_setor,
    CASE
        WHEN fa.cod_agg_familia = 5 THEN 'Setup'
        ELSE 'Disponibilidade'
    END AS tipo_parada
INTO #paradas_com_peso
FROM Paradas       par WITH(NOLOCK)
LEFT JOIN Motivo_Paradas mot WITH(NOLOCK) ON mot.Codigo       = par.Codigo
LEFT JOIN Maquinas       maq WITH(NOLOCK) ON maq.ID           = par.Maquina_ID
LEFT JOIN Pavilhao       pav WITH(NOLOCK) ON pav.ID           = maq.ID_Pavilhao
LEFT JOIN #familias      fa               ON fa.cod_familia   = mot.ID_Familia
WHERE par.Hora_Inicio  <= @DataFimAnalise
  AND par.E3TimeStamp  >= @DataInicioAnalise
  AND mot.PesoOee       = 'Com Peso'
  AND maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
  AND pav.ID_Fabrica  NOT IN (38, 43);

-- ► DEBUG: SELECT COUNT(*) AS cnt_paradas_cp FROM #paradas_com_peso;
-- ► DEBUG: SELECT tipo_parada, COUNT(*) AS cnt FROM #paradas_com_peso GROUP BY tipo_parada;
-- ► DEBUG: SELECT TOP 50 * FROM #paradas_com_peso ORDER BY ts_inicio DESC;

-- ---------------------------------------------------------------------------
-- Passo 11 — #disp: disponibilidade + setup por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#disp') IS NOT NULL DROP TABLE #disp;

SELECT
    p.cod_produto,
    t.data_turno AS data,
    SUM(CASE WHEN p.tipo_parada = 'Disponibilidade'
        THEN DATEDIFF(SECOND,
            CASE WHEN p.ts_inicio > t.inicio_turno THEN p.ts_inicio ELSE t.inicio_turno END,
            CASE WHEN p.ts_fim    < t.fim_turno    THEN p.ts_fim    ELSE t.fim_turno    END)
        ELSE 0 END) AS tempo_disp,
    SUM(CASE WHEN p.tipo_parada = 'Setup'
        THEN DATEDIFF(SECOND,
            CASE WHEN p.ts_inicio > t.inicio_turno THEN p.ts_inicio ELSE t.inicio_turno END,
            CASE WHEN p.ts_fim    < t.fim_turno    THEN p.ts_fim    ELSE t.fim_turno    END)
        ELSE 0 END) AS tempo_setup
INTO #disp
FROM #paradas_com_peso p
JOIN #turnos_grid t
    ON p.ts_inicio < t.fim_turno
   AND p.ts_fim    > t.inicio_turno
   AND p.cod_setor = t.cod_setor
WHERE t.data_turno >= CAST(@DataInicioAnalise AS DATE)
GROUP BY p.cod_produto, t.data_turno;

-- ► DEBUG: SELECT COUNT(*) AS cnt_disp FROM #disp;
-- ► DEBUG: SELECT TOP 50 * FROM #disp ORDER BY data DESC;

-- ---------------------------------------------------------------------------
-- Passo 12 — #qual: qualidade por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#qual') IS NOT NULL DROP TABLE #qual;

SELECT
    pq.NumeroProduto AS cod_produto,
    CAST(
        CASE
            WHEN CAST(pq.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, pq.E3TimeStamp)
            ELSE pq.E3TimeStamp
        END AS DATE
    ) AS data,
    SUM(pq.Ciclo * pq.Valor / pq.pares_batida) AS tempo_qual
INTO #qual
FROM Perdas_Qualidade pq   WITH(NOLOCK)
LEFT JOIN Maquinas       maq WITH(NOLOCK) ON maq.ID      = pq.Maquina_ID
LEFT JOIN Pavilhao       pav WITH(NOLOCK) ON pav.ID      = maq.ID_Pavilhao
LEFT JOIN Motivo_Paradas mp  WITH(NOLOCK) ON mp.Codigo   = pq.Codigo
LEFT JOIN #horarios      h               ON h.cod_setor  = maq.ID_Pavilhao
WHERE maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
  AND pav.ID_Fabrica  NOT IN (38, 43)
  AND mp.PesoOee = 'Com Peso'
  AND CAST(
        CASE
            WHEN CAST(pq.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, pq.E3TimeStamp)
            ELSE pq.E3TimeStamp
        END AS DATE
      ) BETWEEN CAST(@DataInicioAnalise AS DATE) AND CAST(@DataFimAnalise AS DATE)
GROUP BY
    pq.NumeroProduto,
    CAST(
        CASE
            WHEN CAST(pq.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, pq.E3TimeStamp)
            ELSE pq.E3TimeStamp
        END AS DATE
    );

-- ► DEBUG: SELECT COUNT(*) AS cnt_qual FROM #qual;
-- ► DEBUG: SELECT TOP 50 * FROM #qual ORDER BY data DESC;

-- ---------------------------------------------------------------------------
-- Passo 13 — #perf_perdas: performance perdas (QV / Molde Reduzido) por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#perf_perdas') IS NOT NULL DROP TABLE #perf_perdas;

SELECT
    perf.NumeroProduto AS cod_produto,
    CAST(
        CASE
            WHEN CAST(perf.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, perf.E3TimeStamp)
            ELSE perf.E3TimeStamp
        END AS DATE
    ) AS data,
    SUM(perf.Valor * perf.Ciclo) AS tempo_perf_perdas
INTO #perf_perdas
FROM Perdas_Performance perf WITH(NOLOCK)
LEFT JOIN Maquinas     m   WITH(NOLOCK) ON m.ID        = perf.Maquina_ID
LEFT JOIN Pavilhao     pav WITH(NOLOCK) ON pav.ID      = m.ID_Pavilhao
LEFT JOIN Fabricas     f   WITH(NOLOCK) ON f.ID        = pav.ID_Fabrica
LEFT JOIN #horarios    h               ON h.cod_setor  = m.ID_Pavilhao
WHERE pav.ID    NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
  AND f.ID      NOT IN (38, 43)
  AND CAST(
        CASE
            WHEN CAST(perf.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, perf.E3TimeStamp)
            ELSE perf.E3TimeStamp
        END AS DATE
      ) BETWEEN CAST(@DataInicioAnalise AS DATE) AND CAST(@DataFimAnalise AS DATE)
GROUP BY
    perf.NumeroProduto,
    CAST(
        CASE
            WHEN CAST(perf.E3TimeStamp AS TIME) < h.Ini_1_T1
            THEN DATEADD(DAY, -1, perf.E3TimeStamp)
            ELSE perf.E3TimeStamp
        END AS DATE
    );

-- ► DEBUG: SELECT COUNT(*) AS cnt_perf_perdas FROM #perf_perdas;
-- ► DEBUG: SELECT TOP 50 * FROM #perf_perdas ORDER BY data DESC;

-- ---------------------------------------------------------------------------
-- Passo 14 — #saldo_tc: saldo TC dos ciclos por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#saldo_tc') IS NOT NULL DROP TABLE #saldo_tc;

SELECT
    cod_produto COLLATE DATABASE_DEFAULT AS cod_produto,
    data_ciclo AS data,
    SUM(soma_ganho) + SUM(soma_perda) AS saldo_tc
INTO #saldo_tc
FROM #ciclos
GROUP BY cod_produto, data_ciclo;

-- ► DEBUG: SELECT COUNT(*) AS cnt_saldo_tc FROM #saldo_tc;
-- ► DEBUG: SELECT TOP 50 * FROM #saldo_tc ORDER BY data DESC;

-- ---------------------------------------------------------------------------
-- Passo 15 — #oee: join final de todos os componentes por produto+dia
-- ---------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#oee') IS NOT NULL DROP TABLE #oee;

SELECT
    tu.cod_produto,
    tu.data,
    tu.tempo_util,
    COALESCE(d.tempo_disp,         0) AS tempo_disp,
    COALESCE(d.tempo_setup,        0) AS tempo_setup,
    COALESCE(q.tempo_qual,         0) AS tempo_qual,
    COALESCE(pp.tempo_perf_perdas, 0) AS tempo_perf_perdas,
    COALESCE(c.saldo_tc,           0) AS saldo_tc
INTO #oee
FROM #tempo_util     tu
LEFT JOIN #disp        d  ON d.cod_produto  = tu.cod_produto AND d.data  = tu.data
LEFT JOIN #qual        q  ON q.cod_produto  = tu.cod_produto AND q.data  = tu.data
LEFT JOIN #perf_perdas pp ON pp.cod_produto = tu.cod_produto AND pp.data = tu.data
LEFT JOIN #saldo_tc    c  ON c.cod_produto  = tu.cod_produto AND c.data  = tu.data
WHERE tu.tempo_util > 0
  AND (
      @cod_produto_filtro IS NULL
      OR CHARINDEX(',' + tu.cod_produto + ',', ',' + @cod_produto_filtro + ',') > 0
  );

-- ► DEBUG: SELECT COUNT(*) AS cnt_oee FROM #oee;
-- ► DEBUG: SELECT * FROM #oee ORDER BY data, cod_produto;

-- ===========================================================================
-- ETAPA 3: OUTPUT COM OEE CALCULADO
-- ===========================================================================
SELECT
    cod_produto,
    RIGHT(@@SERVERNAME, 3)                                       AS estab,

    -- OEE
    CAST(ROUND(
        (1.0
         - CAST(tempo_disp + tempo_setup               AS FLOAT) / NULLIF(tempo_util, 0)
         - CAST(saldo_tc   + tempo_perf_perdas         AS FLOAT) / NULLIF(tempo_util, 0)
         - CAST(tempo_qual                             AS FLOAT) / NULLIF(tempo_util, 0)
        ) * 100, 2) AS DECIMAL(7, 2))                           AS pct_oee,

    -- Tempo útil em HH:MM:SS
    CONVERT(VARCHAR(8),
        DATEADD(SECOND, tempo_util, '1900-01-01'),
        108)                                                     AS tempo_util_hms,

    -- Hrs Boas = TU * OEE em HH:MM:SS
    CONVERT(VARCHAR(8),
        DATEADD(SECOND,
            CAST(tempo_util *
                (1.0
                 - CAST(tempo_disp + tempo_setup       AS FLOAT) / NULLIF(tempo_util, 0)
                 - CAST(saldo_tc   + tempo_perf_perdas AS FLOAT) / NULLIF(tempo_util, 0)
                 - CAST(tempo_qual                     AS FLOAT) / NULLIF(tempo_util, 0)
                ) AS INT),
            '1900-01-01'),
        108)                                                     AS hrs_boas_hms,

    -- Pilares de perda
    CAST(ROUND(CAST(tempo_disp + tempo_setup           AS FLOAT) / NULLIF(tempo_util, 0) * 100, 2)
        AS DECIMAL(7, 2))                                        AS pct_disp,
    CAST(ROUND(CAST(saldo_tc   + tempo_perf_perdas     AS FLOAT) / NULLIF(tempo_util, 0) * 100, 2)
        AS DECIMAL(7, 2))                                        AS pct_perf,
    CAST(ROUND(CAST(tempo_qual                         AS FLOAT) / NULLIF(tempo_util, 0) * 100, 2)
        AS DECIMAL(7, 2))                                        AS pct_qual,

    data
FROM #oee
ORDER BY data, cod_produto;
