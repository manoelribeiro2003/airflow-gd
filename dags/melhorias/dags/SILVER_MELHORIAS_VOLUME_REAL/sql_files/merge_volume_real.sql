SET XACT_ABORT ON;
SET NOCOUNT ON;

-- Recalcula o volume real por melhoria a partir do staging de produção
-- (dbo.stg_mel_volume_real) cruzado com mel_ganhos. Idempotente por range: o range é
-- definido pela DAG (Airflow Variable MEL_VOLUME_REAL_MONTHS) e injetado em @range_start.
--
-- Chave de cálculo: numero_fap + cod_prod (data_fap define a janela). O JOIN casa
-- mel_ganhos.cod_prod com volume.produto_cod (ADR/design: chave = produto_cod, a FAP
-- referencia o código diretamente). A separação embalagem é EXPLÍCITA e simétrica pelo
-- local de produção: o mesmo cod_prod é reportado em dois estágios (local regular e
-- local de embalagem *0070), então o local *0070 particiona o volume — FAP de embalagem
-- soma só *0070, FAP não-embalagem soma só os demais locais (ver regra no JOIN abaixo).

DECLARE @range_start date = '{{ range_start }}';

BEGIN TRY
  BEGIN TRANSACTION;

  --------------------------------------------------------------------------
  -- 1) Limpa o range recomputado (delete-by-range; PK natural numero_fap+cod_prod+mes_ano)
  --------------------------------------------------------------------------
  DELETE FROM [dbengenharia].[dbo].[mel_volume_real]
  WHERE
    data_inicio >= @range_start;

  --------------------------------------------------------------------------
  -- 2) Recalcula e insere
  --------------------------------------------------------------------------
  -- Só existe volume para melhorias dos tipos Tempo Ciclo, Aglutinação, Consumo e
  -- Troca de Matéria Prima. Os demais tipos ("Outros") usam ganho_previsto fixo e não
  -- dependem de volume, então não entram em mel_volume_real. Strings exatas conforme
  -- seed mel_categoria_melhorias (collation CI_AS = accent-sensitive).
  WITH melhorias AS (
    SELECT DISTINCT
      g.numero_fap
    , g.cod_prod
    , g.setor
    , CAST(g.dt_fap AS date)                   AS data_inicio
    , DATEADD(DAY, 30, CAST(g.dt_fap AS date)) AS data_fim
    FROM [dbengenharia].[dbo].[mel_ganhos] AS g
    WHERE
      g.dt_fap >= @range_start
      AND g.numero_fap IS NOT NULL
      AND g.cod_prod IS NOT NULL
      AND g.tipo_melhoria IN (
        N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
      )
  )

  -- Volume válido: exclui locais de produção desconsiderados (dedup entre locais).
  -- COLLATE DATABASE_DEFAULT normaliza as colunas string vindas do staging (DuckDB
  -- mssql cria varchar como UTF8 Latin1_General_100_CI_AS_SC_UTF8) para a collation do
  -- banco (Latin1_General_CI_AS), evitando conflito de collation nos JOINs/comparações.
, volume_valido AS (
    SELECT
      v.produto_cod COLLATE database_default        AS produto_cod
    , v.local_producao_cod COLLATE database_default AS local_producao_cod
    , CAST(v.reporte_data AS date)                  AS reporte_data
    , v.volume_producao
    FROM [dbengenharia].[dbo].[stg_mel_volume_real] AS v
    WHERE
      NOT EXISTS (
        SELECT 1
        FROM [dbengenharia].[dbo].[mel_local_producao_volume_desconsiderados] AS d
        WHERE
          d.local_producao = v.local_producao_cod COLLATE database_default
      )
  )

  -- Soma por mês calendário dentro da janela [data_fap, data_fap + 30 dias].
, calc AS (
    SELECT
      m.numero_fap
    , m.cod_prod
    , FORMAT(vv.reporte_data, 'MM/yyyy') AS mes_ano
    -- Janela real do mes = intersecao do mes calendario com [dt_fap, dt_fap+30].
    -- Valores constantes por grupo (mes_ano); MAX/MIN evitam inchar o GROUP BY.
    , MAX(CASE
        WHEN m.data_inicio > DATEFROMPARTS(YEAR(vv.reporte_data), MONTH(vv.reporte_data), 1)
          THEN m.data_inicio
        ELSE DATEFROMPARTS(YEAR(vv.reporte_data), MONTH(vv.reporte_data), 1)
      END)                               AS data_inicio
    , MIN(CASE
        WHEN m.data_fim < EOMONTH(vv.reporte_data)
          THEN m.data_fim
        ELSE EOMONTH(vv.reporte_data)
      END)                               AS data_fim
    , SUM(vv.volume_producao)            AS volume
    FROM melhorias AS m
      INNER JOIN volume_valido AS vv
      ON vv.produto_cod = m.cod_prod
        AND vv.reporte_data >= m.data_inicio
        AND vv.reporte_data <= m.data_fim
        -- Regra Embalagem (particao estrita por local de producao):
        -- setor 'Embalagem*' so soma volume do local de embalagem (*0070);
        -- demais setores (e setor NULL) somam apenas locais NAO-embalagem.
        -- Sem isso, o volume *0070 contamina FAPs nao-embalagem, pois o mesmo
        -- cod_prod e reportado tanto no estagio regular quanto no de embalagem.
        AND (
          CASE
            WHEN m.setor LIKE N'Embalagem%'
              THEN CASE WHEN vv.local_producao_cod LIKE '%0070' THEN 1 ELSE 0 END
            ELSE CASE WHEN vv.local_producao_cod LIKE '%0070' THEN 0 ELSE 1 END
          END = 1
        )
    GROUP BY
      m.numero_fap
    , m.cod_prod
    , FORMAT(vv.reporte_data, 'MM/yyyy')
  )

  INSERT INTO [dbengenharia].[dbo].[mel_volume_real] (
    numero_fap
  , cod_prod
  , mes_ano
  , volume
  , data_inicio
  , data_fim
  )
  SELECT
    numero_fap
  , cod_prod
  , mes_ano
  , CAST(ROUND(volume, 0) AS int) AS volume
  , data_inicio
  , data_fim
  FROM calc;

  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0
    ROLLBACK TRANSACTION;
  THROW;
END CATCH;
