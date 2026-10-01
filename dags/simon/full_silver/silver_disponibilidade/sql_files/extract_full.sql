DECLARE @hora_inicio DATETIME
DECLARE @hora_fim DATETIME

SET @hora_inicio = ?
SET @hora_fim = ?

SELECT
    ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as linha,
    ? AS id_estabelecimento,
    Id,
    Maquina_ID,
    Codigo,
    Hora_Inicio,
    E3TimeStamp,
    tempo,
    Turno,
    Status,
    Programa,
    Documento,
    NumeroProduto,
    Efetivo,
    ID_Grupo,
    Ref_Matriz,
    Ferramental,
    Cracha_Operador,
    Cracha_Preparador,
    Cracha_Lider,
    Cracha_Apoio
FROM [Elipse].[dbo].[Paradas] WITH(NOLOCK)
WHERE 
Hora_Inicio between @hora_inicio and @hora_fim OR
E3TimeStamp between @hora_inicio and @hora_fim OR
(Hora_Inicio < @hora_inicio and E3TimeStamp > @hora_fim)