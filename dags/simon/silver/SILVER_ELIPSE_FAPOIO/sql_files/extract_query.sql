-- sqlfluff:dialect:tsql
SELECT
  {estab} AS id_estabelecimento
, [Id]
, [DataHoraInicio]
, [DataHoraFim]
, [CodigoMotivo]
, [Maquina_ID]
, [Status]
, [Tempo]
, [Cracha_Preparador]
, [Cracha_Lider]
FROM [Elipse].[dbo].[Aciona_Apoios]
WHERE
  (datahorainicio >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))
  OR
  (datahorafim >= DATEADD(DAY, -90, CONVERT(DATE, GETDATE())))

-- DataHoraInicio between '2025-02-01 05:25:00' and '2025-03-01 06:00:00'
-- or DataHoraFim between '2025-02-01 05:25:00' and '2025-03-01 06:00:00'
-- or (DataHoraInicio < '2025-02-01 05:25:00' and DataHoraFim > '2025-03-01 06:00:00')
