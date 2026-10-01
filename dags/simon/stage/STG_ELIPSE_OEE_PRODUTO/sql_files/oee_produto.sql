-- sqlfluff:dialect:tsql
-- =============================================================================
-- oee_produto.sql
-- OEE diário por NumeroProduto — últimos 31 dias
--
-- Parâmetros (ajustar no topo):
--   @DataInicioAnalise  : início do período
--   @DataFimAnalise     : fim do período
--   @cod_produto_filtro : NULL = todos | '25122' = um | '25122,06466' = múltiplos (sem espaços)
--
-- Fórmula:
--   OEE = 1 - (tempo_disp + tempo_setup + saldo_tc + tempo_perf_perdas + tempo_qual) / tempo_util
--
-- Notas:
--   - Compatível com SQL Server 2008 (sem STRING_SPLIT, sem IIF)
--   - Tabelas Ciclo X descobertas em Python via discover_tables.sql; UNION ALL injetado via placeholder
--   - WITH (NOLOCK) em todas as tabelas de produção
-- =============================================================================

DECLARE @DataInicioAnalise DATETIME = '{dt_inicio}';
DECLARE @DataFimAnalise DATETIME = '{dt_fim}';
DECLARE @cod_produto_filtro NVARCHAR(MAX) = NULL;

-- ===========================================================================
-- ETAPA 1: SaldoTC dos ciclos (SQL dinâmico — uma tabela Ciclo por máquina)
-- ===========================================================================
IF OBJECT_ID('tempdb..#ciclos') IS NOT NULL DROP TABLE [#ciclos];

CREATE TABLE [#ciclos] (
  [cod_produto] NVARCHAR(50) COLLATE database_default NOT NULL
, [data_ciclo] DATE NOT NULL
, [soma_ganho] FLOAT NOT NULL
, [soma_perda] FLOAT NOT NULL
);

INSERT INTO [#ciclos] ([cod_produto], [data_ciclo], [soma_ganho], [soma_perda])
SELECT
  c.[cod_produto]
, CAST(
    CASE
      WHEN CAST(c.[ts_ciclo] AS TIME) < hor.[Ini_1_T1]
        THEN DATEADD(DAY, -1, c.[ts_ciclo])
      ELSE c.[ts_ciclo]
    END AS DATE
  )                    AS [data_ciclo]
, SUM(c.[ganho_ciclo]) AS [soma_ganho]
, SUM(c.[perda_ciclo]) AS [soma_perda]
FROM (
  {ciclos_union}
) AS c
  LEFT JOIN [Maquinas] m WITH (NOLOCK) ON m.[ID] = c.[cod_maquina]
  LEFT JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = m.[ID_Pavilhao]
  LEFT JOIN [Parametros_Setor] ps WITH (NOLOCK) ON ps.[Setor] = pav.[Pavilhao]
  LEFT JOIN [Horarios] hor WITH (NOLOCK) ON hor.[Nome] = ps.[Horario]
WHERE
  pav.[ID] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
  AND pav.[ID_Fabrica] NOT IN (38, 43)
  AND CAST(
    CASE
      WHEN CAST(c.[ts_ciclo] AS TIME) < hor.[Ini_1_T1]
        THEN DATEADD(DAY, -1, c.[ts_ciclo])
      ELSE c.[ts_ciclo]
    END AS DATE
  ) BETWEEN CAST(@DataInicioAnalise AS DATE) AND CAST(@DataFimAnalise AS DATE)
GROUP BY
  c.[cod_produto]
, CAST(
    CASE
      WHEN CAST(c.[ts_ciclo] AS TIME) < hor.[Ini_1_T1]
        THEN DATEADD(DAY, -1, c.[ts_ciclo])
      ELSE c.[ts_ciclo]
    END AS DATE
  );

-- ===========================================================================
-- ETAPA 2: CTEs das demais fontes
-- ===========================================================================
; WITH

-- Horários de cada setor (base para grade de turnos e ajuste de data)
cte_horarios AS (
  SELECT
    pav.[ID] AS [cod_setor]
  , hor.[Ini_1_T1]
  , hor.[Fim_1_T1]
  , hor.[Ini_1_T2]
  , hor.[Fim_1_T2]
  , hor.[Ini_1_T3]
  , hor.[Fim_1_T3]
  FROM [Pavilhao] pav WITH (NOLOCK)
    LEFT JOIN [Parametros_Setor] ps WITH (NOLOCK) ON ps.[Setor] = pav.[Pavilhao]
    LEFT JOIN [Horarios] hor WITH (NOLOCK) ON hor.[Nome] = ps.[Horario]
  WHERE
    pav.[ID] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
)

-- Grade de dias para construir turnos virtuais
, datasparaanalisar AS (
  SELECT CAST(DATEADD(DAY, -1, @DataInicioAnalise) AS DATE) AS [Dia]
  UNION ALL
  SELECT DATEADD(DAY, 1, [Dia])
  FROM datasparaanalisar
  WHERE
    [Dia] < CAST(@DataFimAnalise AS DATE)
)

-- Grade de turnos por setor+dia (início e fim de cada turno)
, turnosgrid AS (
  -- Turno 1
  SELECT
    h.[cod_setor]
  , d.[Dia]                                                                          AS [data_turno]
  , 1                                                                                AS [num_turno]
  , CAST(CAST(d.[Dia] AS VARCHAR) + ' ' + CAST(h.[Ini_1_T1] AS VARCHAR) AS DATETIME)
      AS [inicio_turno]
  , CAST(CAST(d.[Dia] AS VARCHAR) + ' ' + CAST(h.[Fim_1_T1] AS VARCHAR) AS DATETIME) AS [fim_turno]
  FROM datasparaanalisar d CROSS JOIN cte_horarios h
  UNION ALL
  -- Turno 2
  SELECT
    h.[cod_setor]
  , d.[Dia]
  , 2
  , CAST(CAST(CASE WHEN CAST(h.[Ini_1_T2] AS TIME) < CAST(h.[Ini_1_T1] AS TIME)
        THEN DATEADD(DAY, 1, d.[Dia])
      ELSE d.[Dia]
    END AS VARCHAR)
    + ' ' + CAST(h.[Ini_1_T2] AS VARCHAR) AS DATETIME)
  , CAST(CAST(CASE WHEN CAST(h.[Fim_1_T2] AS TIME) < CAST(h.[Ini_1_T1] AS TIME)
        THEN DATEADD(DAY, 1, d.[Dia])
      ELSE d.[Dia]
    END AS VARCHAR)
    + ' ' + CAST(h.[Fim_1_T2] AS VARCHAR) AS DATETIME)
  FROM datasparaanalisar d CROSS JOIN cte_horarios h
  UNION ALL
  -- Turno 3
  SELECT
    h.[cod_setor]
  , d.[Dia]
  , 3
  , CAST(CAST(CASE WHEN h.[Ini_1_T3] = '00:57:01'
        OR CAST(h.[Ini_1_T3] AS TIME) < CAST(h.[Ini_1_T1] AS TIME)
        THEN DATEADD(DAY, 1, d.[Dia])
      ELSE d.[Dia]
    END AS VARCHAR)
    + ' ' + CAST(h.[Ini_1_T3] AS VARCHAR) AS DATETIME)
  , CAST(CAST(CASE WHEN CAST(h.[Fim_1_T3] AS TIME) < CAST(h.[Ini_1_T3] AS TIME)
        OR h.[Ini_1_T3] = '00:57:01'
        THEN DATEADD(DAY, 1, d.[Dia])
      ELSE d.[Dia]
    END AS VARCHAR)
    + ' ' + CAST(h.[Fim_1_T3] AS VARCHAR) AS DATETIME)
  FROM datasparaanalisar d CROSS JOIN cte_horarios h
)

-- Produtos válidos no período (sem duplicatas)
, cte_produtos_validos AS (
  SELECT
    prod.[ID_Maq]
  , maq.[ID_Pavilhao]                   AS [cod_setor]
  , prod.[NumeroProduto]                AS [cod_produto]
  , prod.[DataInicio]
  , COALESCE(prod.[DataFim], GETDATE()) AS [DataFim]
  , prod.[DataFim]                      AS [DataFim_Original]
  FROM [Produtos] prod WITH (NOLOCK)
    LEFT JOIN [Maquinas] maq WITH (NOLOCK) ON maq.[ID] = prod.[ID_Maq]
    LEFT JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = maq.[ID_Pavilhao]
  WHERE
    prod.[DataInicio] <= @DataFimAnalise
    AND COALESCE(prod.[DataFim], GETDATE()) >= @DataInicioAnalise
    AND maq.[ID_Pavilhao] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
    AND pav.[ID_Fabrica] NOT IN (38, 43)
    AND prod.[ID] NOT IN (
      SELECT p2.[ID]
      FROM [Produtos] p2 WITH (NOLOCK)
        JOIN (
          SELECT
            [ID_Maq]
          , [NumeroProduto]
          , CAST([DataInicio] AS DATETIME2(0)) AS [DataInicioAgrupada]
          FROM [Produtos] WITH (NOLOCK)
          GROUP BY [ID_Maq], [NumeroProduto], CAST([DataInicio] AS DATETIME2(0))
          HAVING COUNT(*) > 1
        ) dup ON p2.[ID_Maq] = dup.[ID_Maq]
          AND p2.[NumeroProduto] = dup.[NumeroProduto]
          AND CAST(p2.[DataInicio] AS DATETIME2(0)) = dup.[DataInicioAgrupada]
      WHERE
        p2.[DataFim] IS NULL
    )
)

-- Paradas sem peso no período
, cte_paradas_sem_peso AS (
  SELECT
    par.*
  FROM [Paradas] par WITH (NOLOCK)
    LEFT JOIN [Motivo_Paradas] mp WITH (NOLOCK) ON mp.[Codigo] = par.[Codigo]
  WHERE
    mp.[PesoOEE] = 'Sem Peso'
    AND par.[Hora_Inicio] <= @DataFimAnalise
    AND par.[E3TimeStamp] >= @DataInicioAnalise
)

-- Interseção produto × parada sem peso (para cálculo de tempo_util)
, cte_prod_parada_sp AS (
  SELECT
    prod.[ID_Maq]
  , prod.[cod_setor]
  , prod.[cod_produto]
  , prod.[DataInicio]
  , prod.[DataFim]
  , CASE
      WHEN par.[Hora_Inicio] < prod.[DataInicio] THEN prod.[DataInicio] ELSE par.[Hora_Inicio]
    END AS [ini_parada]
  , CASE
      WHEN par.[E3TimeStamp] > prod.[DataFim] THEN prod.[DataFim] ELSE par.[E3TimeStamp]
    END AS [fim_parada]
  FROM cte_produtos_validos prod
    LEFT JOIN cte_paradas_sem_peso par
    ON par.[Maquina_ID] = prod.[ID_Maq]
      AND par.[Hora_Inicio] <= prod.[DataFim]
      AND par.[E3TimeStamp] >= prod.[DataInicio]
)

-- Tempo calendário por produto+turno
, agg_calendario AS (
  SELECT
    p.[cod_produto]
  , t.[data_turno]
  , t.[num_turno]
  , t.[cod_setor]
  , SUM(DATEDIFF(
      SECOND
    , CASE WHEN p.[DataInicio] > t.[inicio_turno] THEN p.[DataInicio] ELSE t.[inicio_turno] END
    , CASE WHEN p.[DataFim] < t.[fim_turno] THEN p.[DataFim] ELSE t.[fim_turno] END
    )) AS [tempo_calendario]
  FROM cte_produtos_validos p
    JOIN turnosgrid t
    ON p.[DataInicio] < t.[fim_turno]
      AND p.[DataFim] > t.[inicio_turno]
      AND p.[cod_setor] = t.[cod_setor]
  GROUP BY p.[cod_produto], t.[data_turno], t.[cod_setor], t.[num_turno]
)

-- Tempo sem peso (paradas planejadas) por produto+turno
, agg_sem_peso AS (
  SELECT
    p.[cod_produto]
  , t.[data_turno]
  , t.[num_turno]
  , t.[cod_setor]
  , SUM(DATEDIFF(
      SECOND
    , CASE WHEN p.[ini_parada] > t.[inicio_turno] THEN p.[ini_parada] ELSE t.[inicio_turno] END
    , CASE WHEN p.[fim_parada] < t.[fim_turno] THEN p.[fim_parada] ELSE t.[fim_turno] END
    )) AS [tempo_sem_peso]
  FROM cte_prod_parada_sp p
    JOIN turnosgrid t
    ON p.[ini_parada] < t.[fim_turno]
      AND p.[fim_parada] > t.[inicio_turno]
      AND p.[cod_setor] = t.[cod_setor]
  GROUP BY p.[cod_produto], t.[data_turno], t.[cod_setor], t.[num_turno]
)

-- TEMPO ÚTIL por produto+dia
, cte_tu AS (
  SELECT
    cal.[cod_produto]
  , cal.[data_turno]                      AS [data]
  , SUM(cal.[tempo_calendario])           AS [tempo_calendario]
  , SUM(COALESCE(sp.[tempo_sem_peso], 0)) AS [tempo_sem_peso]
  , SUM(
      CASE
        WHEN COALESCE(sp.[tempo_sem_peso], 0) > cal.[tempo_calendario] THEN 0
        ELSE cal.[tempo_calendario] - COALESCE(sp.[tempo_sem_peso], 0)
      END
    )                                     AS [tempo_util]
  FROM agg_calendario cal
    LEFT JOIN agg_sem_peso sp
    ON sp.[cod_produto] = cal.[cod_produto]
      AND sp.[data_turno] = cal.[data_turno]
      AND sp.[num_turno] = cal.[num_turno]
      AND sp.[cod_setor] = cal.[cod_setor]
  WHERE
    cal.[data_turno] >= CAST(@DataInicioAnalise AS DATE)
  GROUP BY cal.[cod_produto], cal.[data_turno]
)

-- Mapeamento de famílias de parada para grupo OEE
, cte_familias AS (
  SELECT
    [ID] AS [cod_familia]
  , CASE
      WHEN [ID] IN (65, 116, 139) THEN 2  -- Manutenção
      WHEN [ID] IN (66, 115) THEN 3  -- Matrizaria
      WHEN [ID] IN (
          67, 70, 73, 76, 78, 79, 80, 81, 82, 83, 84, 87
        , 119, 120, 121, 122, 137, 138
        ) THEN 1  -- Produção
      WHEN [ID] = 71 THEN 4  -- Tingimento
      WHEN [ID] = 86 THEN 5  -- Setup
      ELSE NULL
    END  AS [cod_agg_familia]
  FROM [Familia_paradas] WITH (NOLOCK)
)

-- Paradas COM PESO no período
, cte_paradas_com_peso AS (
  SELECT
    par.[Maquina_ID]
  , par.[NumeroProduto] AS [cod_produto]
  , par.[Hora_Inicio]   AS [ts_inicio]
  , par.[E3TimeStamp]   AS [ts_fim]
  , maq.[ID_Pavilhao]   AS [cod_setor]
  , CASE
      WHEN fa.[cod_agg_familia] = 5 THEN 'Setup'
      ELSE 'Disponibilidade'
    END                 AS [tipo_parada]
  FROM [Paradas] par WITH (NOLOCK)
    LEFT JOIN [Motivo_Paradas] mot WITH (NOLOCK) ON mot.[Codigo] = par.[Codigo]
    LEFT JOIN [Maquinas] maq WITH (NOLOCK) ON maq.[ID] = par.[Maquina_ID]
    LEFT JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = maq.[ID_Pavilhao]
    LEFT JOIN cte_familias fa ON fa.[cod_familia] = mot.[ID_Familia]
  WHERE
    par.[Hora_Inicio] <= @DataFimAnalise
    AND par.[E3TimeStamp] >= @DataInicioAnalise
    AND mot.[PesoOee] = 'Com Peso'
    AND maq.[ID_Pavilhao] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
    AND pav.[ID_Fabrica] NOT IN (38, 43)
)

-- DISPONIBILIDADE + SETUP por produto+dia
, cte_disp AS (
  SELECT
    p.[cod_produto]
  , t.[data_turno] AS [data]
  , SUM(CASE WHEN p.[tipo_parada] = 'Disponibilidade'
        THEN DATEDIFF(
            SECOND
          , CASE WHEN p.[ts_inicio] > t.[inicio_turno] THEN p.[ts_inicio] ELSE t.[inicio_turno] END
          , CASE WHEN p.[ts_fim] < t.[fim_turno] THEN p.[ts_fim] ELSE t.[fim_turno] END
          )
      ELSE 0
    END)           AS [tempo_disp]
  , SUM(CASE WHEN p.[tipo_parada] = 'Setup'
        THEN DATEDIFF(
            SECOND
          , CASE WHEN p.[ts_inicio] > t.[inicio_turno] THEN p.[ts_inicio] ELSE t.[inicio_turno] END
          , CASE WHEN p.[ts_fim] < t.[fim_turno] THEN p.[ts_fim] ELSE t.[fim_turno] END
          )
      ELSE 0
    END)           AS [tempo_setup]
  FROM cte_paradas_com_peso p
    JOIN turnosgrid t
    ON p.[ts_inicio] < t.[fim_turno]
      AND p.[ts_fim] > t.[inicio_turno]
      AND p.[cod_setor] = t.[cod_setor]
  WHERE
    t.[data_turno] >= CAST(@DataInicioAnalise AS DATE)
  GROUP BY p.[cod_produto], t.[data_turno]
)

-- QUALIDADE por produto+dia
, cte_qual AS (
  SELECT
    pq.[NumeroProduto]                               AS [cod_produto]
  , CAST(
      CASE
        WHEN CAST(pq.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, pq.[E3TimeStamp])
        ELSE pq.[E3TimeStamp]
      END AS DATE
    )                                                AS [data]
  , SUM(pq.[Ciclo] * pq.[Valor] / pq.[pares_batida]) AS [tempo_qual]
  FROM [Perdas_Qualidade] pq WITH (NOLOCK)
    LEFT JOIN [Maquinas] maq WITH (NOLOCK) ON maq.[ID] = pq.[Maquina_ID]
    LEFT JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = maq.[ID_Pavilhao]
    LEFT JOIN [Motivo_Paradas] mp WITH (NOLOCK) ON mp.[Codigo] = pq.[Codigo]
    LEFT JOIN cte_horarios h ON h.[cod_setor] = maq.[ID_Pavilhao]
  WHERE
    maq.[ID_Pavilhao] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
    AND pav.[ID_Fabrica] NOT IN (38, 43)
    AND mp.[PesoOee] = 'Com Peso'
    AND CAST(
      CASE
        WHEN CAST(pq.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, pq.[E3TimeStamp])
        ELSE pq.[E3TimeStamp]
      END AS DATE
    ) BETWEEN CAST(@DataInicioAnalise AS DATE) AND CAST(@DataFimAnalise AS DATE)
  GROUP BY
    pq.[NumeroProduto]
  , CAST(
      CASE
        WHEN CAST(pq.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, pq.[E3TimeStamp])
        ELSE pq.[E3TimeStamp]
      END AS DATE
    )
)

-- PERFORMANCE PERDAS (QV / Molde Reduzido) por produto+dia
, cte_perf_perdas AS (
  SELECT
    perf.[NumeroProduto]             AS [cod_produto]
  , CAST(
      CASE
        WHEN CAST(perf.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, perf.[E3TimeStamp])
        ELSE perf.[E3TimeStamp]
      END AS DATE
    )                                AS [data]
  , SUM(perf.[Valor] * perf.[Ciclo]) AS [tempo_perf_perdas]
  FROM [Perdas_Performance] perf WITH (NOLOCK)
    LEFT JOIN [Maquinas] m WITH (NOLOCK) ON m.[ID] = perf.[Maquina_ID]
    LEFT JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = m.[ID_Pavilhao]
    LEFT JOIN [Fabricas] f WITH (NOLOCK) ON f.[ID] = pav.[ID_Fabrica]
    LEFT JOIN cte_horarios h ON h.[cod_setor] = m.[ID_Pavilhao]
  WHERE
    pav.[ID] NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
    AND f.[ID] NOT IN (38, 43)
    AND CAST(
      CASE
        WHEN CAST(perf.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, perf.[E3TimeStamp])
        ELSE perf.[E3TimeStamp]
      END AS DATE
    ) BETWEEN CAST(@DataInicioAnalise AS DATE) AND CAST(@DataFimAnalise AS DATE)
  GROUP BY
    perf.[NumeroProduto]
  , CAST(
      CASE
        WHEN CAST(perf.[E3TimeStamp] AS TIME) < h.[Ini_1_T1]
          THEN DATEADD(DAY, -1, perf.[E3TimeStamp])
        ELSE perf.[E3TimeStamp]
      END AS DATE
    )
)

-- SALDO TC dos ciclos (de #ciclos, já agregado na Etapa 1)
, cte_ciclos AS (
  SELECT
    [cod_produto] COLLATE database_default AS [cod_produto]
  , [data_ciclo]                           AS [data]
  , SUM([soma_ganho]) + SUM([soma_perda])  AS [saldo_tc]
  FROM [#ciclos]
  GROUP BY [cod_produto], [data_ciclo]
)

-- JOIN FINAL: todos os componentes por produto+dia
, cte_oee AS (
  SELECT
    tu.[cod_produto]
  , tu.[data]
  , tu.[tempo_util]
  , COALESCE(d.[tempo_disp], 0)         AS [tempo_disp]
  , COALESCE(d.[tempo_setup], 0)        AS [tempo_setup]
  , COALESCE(q.[tempo_qual], 0)         AS [tempo_qual]
  , COALESCE(pp.[tempo_perf_perdas], 0) AS [tempo_perf_perdas]
  , COALESCE(c.[saldo_tc], 0)           AS [saldo_tc]
  FROM cte_tu tu
    LEFT JOIN cte_disp d ON d.[cod_produto] = tu.[cod_produto] AND d.[data] = tu.[data]
    LEFT JOIN cte_qual q ON q.[cod_produto] = tu.[cod_produto] AND q.[data] = tu.[data]
    LEFT JOIN cte_perf_perdas pp ON pp.[cod_produto] = tu.[cod_produto] AND pp.[data] = tu.[data]
    LEFT JOIN cte_ciclos c ON c.[cod_produto] = tu.[cod_produto] AND c.[data] = tu.[data]
  WHERE
    tu.[tempo_util] > 0
    AND (
      @cod_produto_filtro IS NULL
      OR CHARINDEX(',' + tu.[cod_produto] + ',', ',' + @cod_produto_filtro + ',') > 0
    )
)

-- ===========================================================================
-- ETAPA 3: OUTPUT COM OEE CALCULADO
-- ===========================================================================
SELECT
  [cod_produto]
, '{estab}'           AS [estab]

  -- OEE
, CAST(ROUND(
    (
      1.0
      - CAST([tempo_disp] + [tempo_setup] AS FLOAT) / NULLIF([tempo_util], 0)
      - CAST([saldo_tc] + [tempo_perf_perdas] AS FLOAT) / NULLIF([tempo_util], 0)
      - CAST([tempo_qual] AS FLOAT) / NULLIF([tempo_util], 0)
    ) * 100, 2
  ) AS DECIMAL(18, 2)) AS [pct_oee]

  -- Tempo útil em HH:MM:SS
, CONVERT(
    VARCHAR(8)
  , DATEADD(SECOND, [tempo_util], '1900-01-01')
  , 108
  )                   AS [tempo_util_hms]

  -- Hrs Boas = TU * OEE em HH:MM:SS
, CONVERT(
    VARCHAR(8)
  , DATEADD(
      SECOND
    , CAST(
        [tempo_util]
        * (
          1.0
          - CAST([tempo_disp] + [tempo_setup] AS FLOAT) / NULLIF([tempo_util], 0)
          - CAST([saldo_tc] + [tempo_perf_perdas] AS FLOAT) / NULLIF([tempo_util], 0)
          - CAST([tempo_qual] AS FLOAT) / NULLIF([tempo_util], 0)
        ) AS INT
      )
    , '1900-01-01'
    )
  , 108
  )                   AS [hrs_boas_hms]

  -- Pilares de perda
, CAST(
    ROUND(CAST([tempo_disp] + [tempo_setup] AS FLOAT) / NULLIF([tempo_util], 0) * 100, 2)
    AS DECIMAL(18, 2)
  )                   AS [pct_disp]
, CAST(
    ROUND(CAST([saldo_tc] + [tempo_perf_perdas] AS FLOAT) / NULLIF([tempo_util], 0) * 100, 2)
    AS DECIMAL(18, 2)
  )                   AS [pct_perf]
, CAST(
    ROUND(CAST([tempo_qual] AS FLOAT) / NULLIF([tempo_util], 0) * 100, 2)
    AS DECIMAL(18, 2)
  )                   AS [pct_qual]

, [data]
FROM cte_oee
ORDER BY [data], [cod_produto]

OPTION (MAXRECURSION 0);
