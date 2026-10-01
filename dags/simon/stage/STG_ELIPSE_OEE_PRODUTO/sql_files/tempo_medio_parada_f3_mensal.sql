-- sqlfluff:dialect:tsql
-- =============================================================================
-- tempo_medio_parada_f3_mensal.sql
-- Tempo medio de parada por motivo na Fabrica 3 (exceto Botas), por mes
--
-- Parametros (ajustar no topo):
--   @DataInicio : primeiro dia produtivo do periodo (inclusive)
--   @DataFim    : ultimo dia produtivo do periodo (inclusive)
--   [#motivos]  : lista de codigos de motivo a calcular (um INSERT por motivo)
--
-- Formula:
--   tempo_medio_parada = SUM(tempo das paradas do motivo) / COUNT(DISTINCT grupo)
--   O denominador conta eventos de setup (grupo de parada), nao paradas soltas:
--   um grupo com tres paradas do mesmo motivo vale 1 evento.
--
-- Regras:
--   - Fabrica 3 (ID_Fabrica = 32), exceto Fabrica 3 Botas (ID_Pavilhao = 49)
--   - Somente paradas 'Com Peso'
--   - Somente motivo flat (bln_motivo_flat = 'Sim' de disponibilidade.sql),
--     que depende do par (Codigo, tp_setup)
--   - tp_setup replica cte_paradas_base de disponibilidade.sql: motivo de setup
--     avulso (ID_Grupo NULL) tem rotulo fixo; parada em grupo herda a descricao
--     do motivo da primeira parada do grupo (cte_setup_lookup)
--   - Codigos 816/826 nao geram tp_setup aqui: em disponibilidade.sql eles so
--     valem fora das fabricas (28, 31, 32), e a F3 esta nessa lista
--   - Dia produtivo comeca em Horarios.Ini_1_T1 do setor (06:00:01 na F3):
--     grupo iniciado as 03:00 de 01/09 pertence ao dia 31/08 (mes 8)
--   - Nada antes de Maquinas.Hora_Criacao e contabilizado (ao criar a maquina
--     o Elipse grava uma parada retroativa de ~3 meses)
--   - O mes do evento vem do inicio do grupo, entao um grupo nunca e partido
--     entre dois meses (diferente de disponibilidade_f3_mensal.sql, que recorta
--     a parada pela janela do mes)
--   - Compativel com SQL Server 2008 R2 (sem IIF, EOMONTH, DATEFROMPARTS)
-- =============================================================================

SET NOCOUNT ON;

DECLARE @DataInicio DATE = '2023-01-01';
DECLARE @DataFim DATE = '2023-12-31';

DECLARE @IdFabrica INT = 32;
DECLARE @IdPavilhaoExcluido INT = 49;
DECLARE @Agora DATETIME = GETDATE();
DECLARE @DataFimLookup DATETIME = CAST(DATEADD(DAY, 1, @DataFim) AS DATETIME);

IF OBJECT_ID('tempdb..#motivos') IS NOT NULL DROP TABLE [#motivos];
IF OBJECT_ID('tempdb..#maquinas') IS NOT NULL DROP TABLE [#maquinas];
IF OBJECT_ID('tempdb..#paradas') IS NOT NULL DROP TABLE [#paradas];
IF OBJECT_ID('tempdb..#setup_lookup') IS NOT NULL DROP TABLE [#setup_lookup];

-- ===========================================================================
-- ETAPA 0: lista de motivos a calcular (adicionar um INSERT por motivo novo)
-- ===========================================================================
CREATE TABLE [#motivos] ([cod_motivo] INT NOT NULL PRIMARY KEY);

INSERT INTO [#motivos] ([cod_motivo]) VALUES (100);   -- Troca de Cor

-- ===========================================================================
-- ETAPA 1: maquinas da F3 + janela [ts_ini, ts_fim) do periodo em cada uma
-- ===========================================================================
CREATE TABLE [#maquinas] (
  [id_maquina] INT NOT NULL PRIMARY KEY
, [seg_inicio_dia] INT NOT NULL
, [ts_ini] DATETIME NOT NULL
, [ts_fim] DATETIME NOT NULL
);

INSERT INTO [#maquinas] ([id_maquina], [seg_inicio_dia], [ts_ini], [ts_fim])
SELECT
  m.[id_maquina]
, m.[seg_inicio_dia]
, CASE WHEN lim.[ts_ini] > m.[Hora_Criacao] THEN lim.[ts_ini] ELSE m.[Hora_Criacao] END
    AS [ts_ini]
, CASE WHEN lim.[ts_fim] < @Agora THEN lim.[ts_fim] ELSE @Agora END
    AS [ts_fim]
FROM (
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
) m
  CROSS APPLY (
    SELECT
      DATEADD(SECOND, m.[seg_inicio_dia], CAST(@DataInicio AS DATETIME)) AS [ts_ini]
    , DATEADD(SECOND, m.[seg_inicio_dia], @DataFimLookup)                AS [ts_fim]
  ) lim;

DELETE FROM [#maquinas]
WHERE
  [ts_ini] >= [ts_fim];

-- ===========================================================================
-- ETAPA 2: paradas dos motivos pedidos dentro da janela de cada maquina
-- (o mes vem do inicio do grupo, entao a parada nao e recortada pelo mes)
-- ===========================================================================
CREATE TABLE [#paradas] (
  [id_maquina] INT NOT NULL
, [seg_inicio_dia] INT NOT NULL
, [cod_motivo] INT NOT NULL
, [id_grupo] INT NULL
, [ts_ini] DATETIME NOT NULL
, [ts_fim] DATETIME NOT NULL
);

INSERT INTO [#paradas] (
  [id_maquina], [seg_inicio_dia], [cod_motivo], [id_grupo], [ts_ini], [ts_fim]
)
SELECT
  par.[Maquina_ID]
, maq.[seg_inicio_dia]
, par.[Codigo]
, par.[ID_Grupo]
, par.[Hora_Inicio]
, CASE WHEN par.[E3TimeStamp] < maq.[ts_fim] THEN par.[E3TimeStamp] ELSE maq.[ts_fim] END
    AS [ts_fim]
FROM [Paradas] par WITH (NOLOCK)
  JOIN [#maquinas] maq ON maq.[id_maquina] = par.[Maquina_ID]
  JOIN [#motivos] mv ON mv.[cod_motivo] = par.[Codigo]
  JOIN [Motivo_Paradas] mot WITH (NOLOCK) ON mot.[Codigo] = par.[Codigo]
WHERE
  par.[Hora_Inicio] >= maq.[ts_ini]
  AND par.[Hora_Inicio] < maq.[ts_fim]
  AND par.[Hora_Inicio] < par.[E3TimeStamp]
  AND mot.[PesoOee] = 'Com Peso';

CREATE CLUSTERED INDEX [ix_paradas] ON [#paradas] ([id_grupo], [id_maquina]);

-- ===========================================================================
-- ETAPA 3: tp_setup do grupo = descricao do motivo da 1a parada do grupo
-- (mesma regra de cte_setup_lookup em disponibilidade.sql)
-- ===========================================================================
SELECT
  [id_grupo]
, [tp_setup]
INTO [#setup_lookup]
FROM (
  SELECT
    g.[ID_Grupo]                                                               AS [id_grupo]
  , gm.[Descricao]                                                             AS [tp_setup]
  , ROW_NUMBER() OVER (PARTITION BY g.[ID_Grupo] ORDER BY g.[Hora_Inicio] ASC) AS [rn]
  FROM [Paradas] g WITH (NOLOCK)
    JOIN [Motivo_Paradas] gm WITH (NOLOCK) ON gm.[Codigo] = g.[Codigo]
  WHERE
    g.[ID_Grupo] IN (
      SELECT [id_grupo] FROM [#paradas]
      WHERE
        [id_grupo] IS NOT NULL
    )
    AND g.[Tempo] = 1
    AND g.[Codigo] NOT IN (0, 106, 1614)
    AND g.[Hora_Inicio] <= @DataFimLookup
) sub
WHERE
  [rn] = 1;

CREATE CLUSTERED INDEX [ix_setup_lookup] ON [#setup_lookup] ([id_grupo]);

-- ===========================================================================
-- ETAPA 4: agregacao
-- ===========================================================================
WITH

-- tp_setup por parada (motivo de setup avulso tem rotulo fixo)
cte_tp_setup AS (
  SELECT
    p.[id_maquina]
  , p.[seg_inicio_dia]
  , p.[cod_motivo]
  , p.[id_grupo]
  , p.[ts_ini]
  , DATEDIFF(SECOND, p.[ts_ini], p.[ts_fim]) AS [seg]
  , CASE
      WHEN p.[cod_motivo] = 100 AND p.[id_grupo] IS NULL THEN 'Troca de Cor'
      WHEN p.[cod_motivo] = 107 AND p.[id_grupo] IS NULL THEN 'Setup Matriz'
      WHEN p.[cod_motivo] = 125 AND p.[id_grupo] IS NULL THEN 'Troca de Layout'
      WHEN p.[cod_motivo] = 126 AND p.[id_grupo] IS NULL THEN 'Troca Numeracao'
      WHEN p.[cod_motivo] = 149 AND p.[id_grupo] IS NULL THEN 'Troca de Produto'
      WHEN p.[cod_motivo] = 400 AND p.[id_grupo] IS NULL THEN 'Setup Matriz'
      WHEN p.[cod_motivo] = 402 AND p.[id_grupo] IS NULL THEN 'Troca de coleção'
      WHEN p.[cod_motivo] = 892 AND p.[id_grupo] IS NULL
        THEN 'Troca de Cor com Limpeza de Bico'
      WHEN p.[cod_motivo] = 1701 AND p.[id_grupo] IS NULL THEN 'Troca de Cor com Glitter'
      WHEN p.[cod_motivo] = 1728 AND p.[id_grupo] IS NULL THEN 'Setup de Matriz e Cor'
      ELSE COALESCE(sl.[tp_setup], '')
    END                                      AS [tp_setup]
  FROM [#paradas] p
    LEFT JOIN [#setup_lookup] sl ON sl.[id_grupo] = p.[id_grupo]
)

-- Somente motivo flat; chave do evento = grupo (ou a propria parada, quando
-- o motivo de setup e avulso e nao tem ID_Grupo)
, cte_flat AS (
  SELECT
    t.[cod_motivo]
  , t.[seg]
  , DATEADD(SECOND, -t.[seg_inicio_dia], t.[ts_ini]) AS [ts_dia_produtivo]
  , CASE
      WHEN t.[id_grupo] IS NULL
        THEN 'S' + CAST(t.[id_maquina] AS VARCHAR(20))
          + '_' + CONVERT(VARCHAR(23), t.[ts_ini], 121)
      ELSE 'G' + CAST(t.[id_grupo] AS VARCHAR(20))
    END                                              AS [cod_grupo_parada]
  FROM cte_tp_setup t
  WHERE
    CASE
      WHEN (t.[cod_motivo] IN (107, 454, 1704, 400, 1041, 129) AND t.[tp_setup] = 'Setup Matriz')
        OR (t.[cod_motivo] IN (100, 1707, 1708, 129) AND t.[tp_setup] = 'Troca de Cor')
        OR (t.[cod_motivo] IN (892, 1701))
        THEN 'Sim'
      ELSE ''
    END = 'Sim'
)

-- Um evento por grupo+motivo: mes vem do inicio do grupo
, cte_eventos AS (
  SELECT
    [cod_motivo]
  , [cod_grupo_parada]
  , MIN([ts_dia_produtivo])    AS [ts_evento]
  , COUNT(*)                   AS [qtd_paradas]
  , SUM(CAST([seg] AS BIGINT)) AS [seg_evento]
  FROM cte_flat
  GROUP BY [cod_motivo], [cod_grupo_parada]
)

, cte_final AS (
  SELECT
    YEAR([ts_evento])                                         AS [ano]
  , MONTH([ts_evento])                                        AS [mes]
  , [cod_motivo]
  , COUNT(*)                                                  AS [qtd_grupos]
  , SUM([qtd_paradas])                                        AS [qtd_paradas]
  , SUM([seg_evento])                                         AS [seg_total]
  , CAST(ROUND(1.0 * SUM([seg_evento]) / COUNT(*), 0) AS INT) AS [seg_medio]
  FROM cte_eventos
  GROUP BY YEAR([ts_evento]), MONTH([ts_evento]), [cod_motivo]
)

SELECT
  f.[ano]
, f.[mes]
, f.[cod_motivo]
, mot.[Descricao]                                                AS [des_motivo]
, f.[qtd_grupos]
, f.[qtd_paradas]
, CAST(f.[seg_total] / 3600.0 AS DECIMAL(18, 2))                 AS [horas_parada]
, CAST(f.[seg_medio] / 3600 AS VARCHAR(10))
  + ':' + RIGHT('0' + CAST((f.[seg_medio] % 3600) / 60 AS VARCHAR(2)), 2)
  + ':' + RIGHT('0' + CAST(f.[seg_medio] % 60 AS VARCHAR(2)), 2)
    AS [tempo_medio_parada]
FROM cte_final f
  LEFT JOIN [Motivo_Paradas] mot WITH (NOLOCK) ON mot.[Codigo] = f.[cod_motivo]
ORDER BY f.[ano], f.[mes], f.[cod_motivo];

DROP TABLE [#motivos];
DROP TABLE [#maquinas];
DROP TABLE [#paradas];
DROP TABLE [#setup_lookup];
