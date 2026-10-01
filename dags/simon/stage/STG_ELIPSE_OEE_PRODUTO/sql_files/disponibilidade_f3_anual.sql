-- sqlfluff:dialect:tsql
-- =============================================================================
-- disponibilidade_f3_anual.sql
-- % Disponibilidade da Fábrica 3 (exceto Botas) por ano
-- (mesma lógica de disponibilidade_f3_mensal.sql; só muda a agregação final)
--
-- Parâmetros (ajustar no topo):
--   @DataInicio : primeiro dia produtivo do período (inclusive)
--   @DataFim    : último dia produtivo do período (inclusive)
--
-- Fórmulas (convenção SiMOn: % = tempo parado / tempo útil):
--   pct_disp_total        = paradas com peso (família <> Setup) / tempo_util
--   pct_disp_manutencao   = paradas com peso família Manutenção / tempo_util
--   pct_disp_matrizaria   = paradas com peso família Matrizaria / tempo_util
--   pct_disp_manut_matriz = Manutenção + Matrizaria              / tempo_util
--   pct_setup             = paradas com peso família Setup       / tempo_util
--   tempo_util            = tempo com produto programado - paradas sem peso
--
-- Regras:
--   - Fábrica 3 (ID_Fabrica = 32), exceto Fabrica 3 Botas (ID_Pavilhao = 49)
--   - Dia produtivo começa em Horarios.Ini_1_T1 do setor (06:00:01 na F3):
--     parada às 03:00 de 01/09 pertence ao dia 31/08 (mês 8)
--   - Nada antes de Maquinas.Hora_Criacao é contabilizado (ao criar a máquina
--     o Elipse grava uma parada retroativa de ~3 meses)
--   - Setup segue disponibilidade.sql: parada de grupo de setup (ID_Grupo) ou
--     motivo de setup avulso conta como Setup, mesmo sendo Manutenção/Matrizaria
--     (códigos 816/826 não entram: em disponibilidade.sql valem só fora da F3)
--   - Compatível com SQL Server 2008 R2 (sem IIF, EOMONTH, DATEFROMPARTS)
-- =============================================================================

SET NOCOUNT ON;

DECLARE @DataInicio DATE = '2023-01-01';
DECLARE @DataFim DATE = '2023-12-31';

DECLARE @IdFabrica INT = 32;
DECLARE @IdPavilhaoExcluido INT = 49;
DECLARE @Agora DATETIME = GETDATE();

IF OBJECT_ID('tempdb..#periodos') IS NOT NULL DROP TABLE [#periodos];
IF OBJECT_ID('tempdb..#produtos') IS NOT NULL DROP TABLE [#produtos];
IF OBJECT_ID('tempdb..#paradas') IS NOT NULL DROP TABLE [#paradas];
IF OBJECT_ID('tempdb..#grupos_setup') IS NOT NULL DROP TABLE [#grupos_setup];

-- ===========================================================================
-- ETAPA 1: janela [ts_ini, ts_fim) de cada máquina em cada mês, recortada
-- pelo período, pela data de criação da máquina e pelo instante atual
-- ===========================================================================
CREATE TABLE [#periodos] (
  [id_maquina] INT NOT NULL
, [ano] INT NOT NULL
, [mes] INT NOT NULL
, [ts_ini] DATETIME NOT NULL
, [ts_fim] DATETIME NOT NULL
);

WITH

-- Máquinas da F3 + segundos entre 00:00 e o início do dia produtivo do setor
cte_maquinas AS (
  SELECT
    maq.[ID]                                              AS [id_maquina]
  , maq.[Hora_Criacao]
  , DATEDIFF(SECOND, 0, CAST(hor.[Ini_1_T1] AS DATETIME)) AS [seg_inicio_dia]
  FROM [Maquinas] maq WITH (NOLOCK)
    JOIN [Pavilhao] pav WITH (NOLOCK) ON pav.[ID] = maq.[ID_Pavilhao]
    JOIN [Parametros_Setor] ps WITH (NOLOCK) ON ps.[Setor] = pav.[Pavilhao]
    JOIN [Horarios] hor WITH (NOLOCK) ON hor.[Nome] = ps.[Horario]
  WHERE
    pav.[ID_Fabrica] = @IdFabrica
    AND maq.[ID_Pavilhao] <> @IdPavilhaoExcluido
)

-- Grade de meses do período
, cte_meses AS (
  SELECT DATEADD(MONTH, DATEDIFF(MONTH, 0, CAST(@DataInicio AS DATETIME)), 0) AS [ini_mes]
  UNION ALL
  SELECT DATEADD(MONTH, 1, [ini_mes])
  FROM cte_meses
  WHERE
    DATEADD(MONTH, 1, [ini_mes]) <= CAST(@DataFim AS DATETIME)
)

, cte_periodos AS (
  SELECT
    m.[id_maquina]
  , YEAR(me.[ini_mes])                                                                    AS [ano]
  , MONTH(me.[ini_mes])                                                                   AS [mes]
  , CASE WHEN lim.[ts_ini] > m.[Hora_Criacao] THEN lim.[ts_ini] ELSE m.[Hora_Criacao] END
      AS [ts_ini]
  , CASE WHEN lim.[ts_fim] < @Agora THEN lim.[ts_fim] ELSE @Agora END
      AS [ts_fim]
  FROM cte_maquinas m
    CROSS JOIN cte_meses me
    CROSS APPLY (
      SELECT
        DATEADD(
          SECOND
        , m.[seg_inicio_dia]
        , CASE
            WHEN me.[ini_mes] > CAST(@DataInicio AS DATETIME) THEN me.[ini_mes]
            ELSE CAST(@DataInicio AS DATETIME)
          END
        ) AS [ts_ini]
      , DATEADD(
          SECOND
        , m.[seg_inicio_dia]
        , CASE
            WHEN DATEADD(MONTH, 1, me.[ini_mes]) < CAST(DATEADD(DAY, 1, @DataFim) AS DATETIME)
              THEN DATEADD(MONTH, 1, me.[ini_mes])
            ELSE CAST(DATEADD(DAY, 1, @DataFim) AS DATETIME)
          END
        ) AS [ts_fim]
    ) lim
)

INSERT INTO [#periodos] ([id_maquina], [ano], [mes], [ts_ini], [ts_fim])
SELECT [id_maquina], [ano], [mes], [ts_ini], [ts_fim]
FROM cte_periodos
WHERE
  [ts_ini] < [ts_fim]
OPTION (MAXRECURSION 0);

CREATE CLUSTERED INDEX [ix_periodos] ON [#periodos] ([id_maquina], [ts_ini]);

-- ===========================================================================
-- ETAPA 2: produtos programados na janela de cada máquina
-- ===========================================================================
CREATE TABLE [#produtos] (
  [id_produto] BIGINT NOT NULL
, [id_maquina] INT NOT NULL
, [cod_produto] VARCHAR(10) COLLATE database_default NULL
, [ts_ini] DATETIME NOT NULL
, [ts_fim] DATETIME NOT NULL
, [bln_fim_nulo] BIT NOT NULL
);

INSERT INTO [#produtos] (
  [id_produto], [id_maquina], [cod_produto], [ts_ini], [ts_fim], [bln_fim_nulo]
)
SELECT
  prod.[ID]                                          AS [id_produto]
, prod.[ID_Maq]                                      AS [id_maquina]
, prod.[NumeroProduto]                               AS [cod_produto]
, prod.[DataInicio]                                  AS [ts_ini]
, COALESCE(prod.[DataFim], @Agora)                   AS [ts_fim]
, CASE WHEN prod.[DataFim] IS NULL THEN 1 ELSE 0 END AS [bln_fim_nulo]
FROM [Produtos] prod WITH (NOLOCK)
  JOIN (
    SELECT [id_maquina], MIN([ts_ini]) AS [ts_ini], MAX([ts_fim]) AS [ts_fim]
    FROM [#periodos]
    GROUP BY [id_maquina]
  ) j ON j.[id_maquina] = prod.[ID_Maq]
WHERE
  prod.[DataInicio] < j.[ts_fim]
  AND COALESCE(prod.[DataFim], @Agora) > j.[ts_ini];

-- Mesma regra de duplicados de tempo_util.sql: produto em aberto com outro
-- registro de mesma máquina+produto+DataInicio (ao segundo) é descartado
DELETE p
FROM [#produtos] p
WHERE
  p.[bln_fim_nulo] = 1
  AND EXISTS (
    SELECT 1
    FROM [Produtos] dup WITH (NOLOCK)
    WHERE
      dup.[ID_Maq] = p.[id_maquina]
      AND dup.[NumeroProduto] = p.[cod_produto]
      AND CAST(dup.[DataInicio] AS DATETIME2(0)) = CAST(p.[ts_ini] AS DATETIME2(0))
      AND dup.[ID] <> p.[id_produto]
  );

CREATE CLUSTERED INDEX [ix_produtos] ON [#produtos] ([id_maquina], [ts_ini]);

-- ===========================================================================
-- ETAPA 3: paradas (com e sem peso) na janela de cada máquina
-- ===========================================================================
CREATE TABLE [#paradas] (
  [id_maquina] INT NOT NULL
, [cod_motivo] INT NOT NULL
, [id_grupo] INT NULL
, [id_familia] INT NULL
, [bln_com_peso] BIT NOT NULL
, [ts_ini] DATETIME NOT NULL
, [ts_fim] DATETIME NOT NULL
);

INSERT INTO [#paradas] (
  [id_maquina], [cod_motivo], [id_grupo], [id_familia], [bln_com_peso], [ts_ini], [ts_fim]
)
SELECT
  par.[Maquina_ID]                                       AS [id_maquina]
, par.[Codigo]                                           AS [cod_motivo]
, par.[ID_Grupo]                                         AS [id_grupo]
, mot.[ID_Familia]                                       AS [id_familia]
, CASE WHEN mot.[PesoOee] = 'Com Peso' THEN 1 ELSE 0 END AS [bln_com_peso]
, par.[Hora_Inicio]                                      AS [ts_ini]
, par.[E3TimeStamp]                                      AS [ts_fim]
FROM [Paradas] par WITH (NOLOCK)
  JOIN (
    SELECT [id_maquina], MIN([ts_ini]) AS [ts_ini], MAX([ts_fim]) AS [ts_fim]
    FROM [#periodos]
    GROUP BY [id_maquina]
  ) j ON j.[id_maquina] = par.[Maquina_ID]
  JOIN [Motivo_Paradas] mot WITH (NOLOCK) ON mot.[Codigo] = par.[Codigo]
WHERE
  par.[Hora_Inicio] < j.[ts_fim]
  AND par.[E3TimeStamp] > j.[ts_ini]
  AND par.[Hora_Inicio] < par.[E3TimeStamp]
  AND mot.[PesoOee] IN ('Com Peso', 'Sem Peso');

CREATE CLUSTERED INDEX [ix_paradas] ON [#paradas] ([id_maquina], [ts_ini]);

-- Grupos de setup: equivalente a tp_setup <> '' via cte_setup_lookup de
-- disponibilidade.sql (1ª parada do grupo com Tempo = 1 e motivo válido)
SELECT DISTINCT p.[id_grupo]
INTO [#grupos_setup]
FROM [#paradas] p
WHERE
  p.[bln_com_peso] = 1
  AND p.[id_grupo] IS NOT NULL
  AND EXISTS (
    SELECT 1
    FROM [Paradas] g WITH (NOLOCK)
      JOIN [Motivo_Paradas] gm WITH (NOLOCK) ON gm.[Codigo] = g.[Codigo]
    WHERE
      g.[ID_Grupo] = p.[id_grupo]
      AND g.[Tempo] = 1
      AND g.[Codigo] NOT IN (0, 106, 1614)
      AND g.[Hora_Inicio] <= CAST(DATEADD(DAY, 1, @DataFim) AS DATETIME)
      AND gm.[Descricao] <> ''
  );

-- ===========================================================================
-- ETAPA 4: agregação
-- ===========================================================================
WITH

-- Tempo com produto programado por produto+mês
cte_calendario AS (
  SELECT
    pe.[id_maquina]
  , pe.[ano]
  , pe.[mes]
  , pr.[id_produto]
  , DATEDIFF(
      SECOND
    , CASE WHEN pr.[ts_ini] > pe.[ts_ini] THEN pr.[ts_ini] ELSE pe.[ts_ini] END
    , CASE WHEN pr.[ts_fim] < pe.[ts_fim] THEN pr.[ts_fim] ELSE pe.[ts_fim] END
    ) AS [seg_calendario]
  FROM [#produtos] pr
    JOIN [#periodos] pe
    ON pe.[id_maquina] = pr.[id_maquina]
      AND pr.[ts_ini] < pe.[ts_fim]
      AND pr.[ts_fim] > pe.[ts_ini]
)

-- Paradas sem peso dentro da programação do produto, por produto+mês
, cte_sem_peso AS (
  SELECT
    pe.[id_maquina]
  , pe.[ano]
  , pe.[mes]
  , pr.[id_produto]
  , SUM(DATEDIFF(SECOND, ini.[ts], fim.[ts])) AS [seg_sem_peso]
  FROM [#paradas] sp
    JOIN [#produtos] pr
    ON pr.[id_maquina] = sp.[id_maquina]
      AND sp.[ts_ini] < pr.[ts_fim]
      AND sp.[ts_fim] > pr.[ts_ini]
    JOIN [#periodos] pe
    ON pe.[id_maquina] = sp.[id_maquina]
      AND sp.[ts_ini] < pe.[ts_fim]
      AND sp.[ts_fim] > pe.[ts_ini]
    CROSS APPLY (
      SELECT MAX(v) AS [ts] FROM (VALUES (sp.[ts_ini]), (pr.[ts_ini]), (pe.[ts_ini])) t (v)
    ) ini
    CROSS APPLY (
      SELECT MIN(v) AS [ts] FROM (VALUES (sp.[ts_fim]), (pr.[ts_fim]), (pe.[ts_fim])) t (v)
    ) fim
  WHERE
    sp.[bln_com_peso] = 0
    AND ini.[ts] < fim.[ts]
  GROUP BY pe.[id_maquina], pe.[ano], pe.[mes], pr.[id_produto]
)

-- TEMPO ÚTIL por ano (sem peso maior que o calendário zera, como em tempo_util.sql;
-- o recorte segue por produto+mês para bater com o arquivo mensal)
, cte_tempo_util AS (
  SELECT
    cal.[ano]
  , COUNT(DISTINCT cal.[id_maquina]) AS [qtd_maquinas]
  , SUM(CAST(
      CASE
        WHEN COALESCE(sp.[seg_sem_peso], 0) > cal.[seg_calendario] THEN 0
        ELSE cal.[seg_calendario] - COALESCE(sp.[seg_sem_peso], 0)
      END AS BIGINT
    ))                               AS [seg_util]
  FROM cte_calendario cal
    LEFT JOIN cte_sem_peso sp
    ON sp.[id_maquina] = cal.[id_maquina]
      AND sp.[ano] = cal.[ano]
      AND sp.[mes] = cal.[mes]
      AND sp.[id_produto] = cal.[id_produto]
  GROUP BY cal.[ano]
)

-- Paradas com peso classificadas (Setup > Manutenção > Matrizaria > Outras)
, cte_com_peso AS (
  SELECT
    p.[id_maquina]
  , p.[ts_ini]
  , p.[ts_fim]
  , CASE
      WHEN p.[id_familia] = 86 THEN 'Setup'
      WHEN gs.[id_grupo] IS NOT NULL THEN 'Setup'
      WHEN p.[id_grupo] IS NULL
        AND p.[cod_motivo] IN (100, 107, 125, 126, 149, 400, 402, 892, 1701, 1728)
        THEN 'Setup'
      WHEN p.[id_familia] IN (65, 116, 139) THEN 'Manutencao'
      WHEN p.[id_familia] IN (66, 115) THEN 'Matrizaria'
      ELSE 'Outras'
    END AS [des_familia]
  FROM [#paradas] p
    LEFT JOIN [#grupos_setup] gs ON gs.[id_grupo] = p.[id_grupo]
  WHERE
    p.[bln_com_peso] = 1
)

-- Tempo das paradas com peso por família+ano
, cte_disp AS (
  SELECT
    pe.[ano]
  , SUM(CAST(CASE WHEN cp.[des_familia] <> 'Setup' THEN seg.[seg] ELSE 0 END AS BIGINT))
      AS [seg_disp_total]
  , SUM(CAST(CASE WHEN cp.[des_familia] = 'Manutencao' THEN seg.[seg] ELSE 0 END AS BIGINT))
      AS [seg_manutencao]
  , SUM(CAST(CASE WHEN cp.[des_familia] = 'Matrizaria' THEN seg.[seg] ELSE 0 END AS BIGINT))
      AS [seg_matrizaria]
  , SUM(CAST(CASE WHEN cp.[des_familia] = 'Setup' THEN seg.[seg] ELSE 0 END AS BIGINT))
      AS [seg_setup]
  FROM cte_com_peso cp
    JOIN [#periodos] pe
    ON pe.[id_maquina] = cp.[id_maquina]
      AND cp.[ts_ini] < pe.[ts_fim]
      AND cp.[ts_fim] > pe.[ts_ini]
    CROSS APPLY (
      SELECT DATEDIFF(
        SECOND
      , CASE WHEN cp.[ts_ini] > pe.[ts_ini] THEN cp.[ts_ini] ELSE pe.[ts_ini] END
      , CASE WHEN cp.[ts_fim] < pe.[ts_fim] THEN cp.[ts_fim] ELSE pe.[ts_fim] END
      ) AS [seg]
    ) seg
  GROUP BY pe.[ano]
)

-- Tempo útil + paradas em segundos por ano
, cte_final AS (
  SELECT
    tu.[ano]
  , tu.[qtd_maquinas]
  , tu.[seg_util]
  , COALESCE(d.[seg_disp_total], 0)                                   AS [seg_disp_total]
  , COALESCE(d.[seg_manutencao], 0)                                   AS [seg_manutencao]
  , COALESCE(d.[seg_matrizaria], 0)                                   AS [seg_matrizaria]
  , COALESCE(d.[seg_manutencao], 0) + COALESCE(d.[seg_matrizaria], 0) AS [seg_manut_matriz]
  , COALESCE(d.[seg_setup], 0)                                        AS [seg_setup]
  FROM cte_tempo_util tu
    LEFT JOIN cte_disp d ON d.[ano] = tu.[ano]
)

-- CAST para DECIMAL já arredonda em 2 casas
SELECT
  [ano]
, [qtd_maquinas]
, CAST([seg_util] / 3600.0 AS DECIMAL(18, 2))                               AS [horas_util]
, CAST([seg_disp_total] / 3600.0 AS DECIMAL(18, 2))                         AS [horas_disp_total]
, CAST([seg_manutencao] / 3600.0 AS DECIMAL(18, 2))                         AS [horas_manutencao]
, CAST([seg_matrizaria] / 3600.0 AS DECIMAL(18, 2))                         AS [horas_matrizaria]
, CAST([seg_setup] / 3600.0 AS DECIMAL(18, 2))                              AS [horas_setup]
, CAST(100.0 * [seg_disp_total] / NULLIF([seg_util], 0) AS DECIMAL(9, 2))   AS [pct_disp_total]
, CAST(100.0 * [seg_manutencao] / NULLIF([seg_util], 0) AS DECIMAL(9, 2))   AS [pct_disp_manutencao]
, CAST(100.0 * [seg_matrizaria] / NULLIF([seg_util], 0) AS DECIMAL(9, 2))   AS [pct_disp_matrizaria]
, CAST(100.0 * [seg_manut_matriz] / NULLIF([seg_util], 0) AS DECIMAL(9, 2))
    AS [pct_disp_manut_matriz]
, CAST(100.0 * [seg_setup] / NULLIF([seg_util], 0) AS DECIMAL(9, 2))        AS [pct_setup]
FROM cte_final
ORDER BY [ano];

DROP TABLE [#periodos];
DROP TABLE [#produtos];
DROP TABLE [#paradas];
DROP TABLE [#grupos_setup];
