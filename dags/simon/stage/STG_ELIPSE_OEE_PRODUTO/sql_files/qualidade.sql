DECLARE @DataInicioAnalise DATETIME = GETDATE() - 5;
DECLARE @DataFimAnalise DATETIME = GETDATE();

WITH cte_horarios_setor AS (
	SELECT
		pav.ID AS cod_setor,
		pav.Pavilhao as des_setor,
		hor.Ini_1_T1, hor.Fim_1_T1,
		hor.Ini_1_T2, hor.Fim_1_T2,
		hor.Ini_1_T3, hor.Fim_1_T3
	FROM 
		Pavilhao pav WITH (NOLOCK)
	LEFT JOIN Parametros_Setor param WITH (NOLOCK)
			ON param.Setor = pav.Pavilhao
	LEFT JOIN 
		Horarios hor WITH (NOLOCK)
			ON hor.Nome = param.Horario
	WHERE pav.ID NOT IN (52, 69, 74, 59, 50, 36, 70, 66)
), 

cte_qualidade AS(
	SELECT 
		'20' AS cod_estabelecimento,
		CAST(
			CASE
				WHEN CAST(pq.E3TimeStamp AS TIME) >= '00:00:00' AND CAST(pq.E3TimeStamp AS TIME) < h.Ini_1_T1
				THEN DATEADD(DAY, -1, pq.E3TimeStamp)
				ELSE pq.E3TimeStamp
			END
		AS DATE) AS data_apontamento,
		pq.Maquina_ID AS cod_maquina,
		maq.Nome AS des_nome_maquina,
		pq.NumeroProduto AS cod_produto,
		pq.Programa as num_programa,
	    pq.Documento as num_documento,
		SUBSTRING(pq.Turno, 7, 1) AS num_turno,
		pq.Codigo AS cod_motivo_apontamento,
		mp.Descricao AS des_motivo_apontamento,
	    pq.Ciclo * pq.Valor/ pq.pares_batida as tempo_apontamento,
	    pq.Valor as qtd_pares_perda,
	    '20' + CAST(pq.Maquina_ID AS VARCHAR) AS chave_maquina
	FROM 
		Perdas_Qualidade pq WITH (NOLOCK)
	LEFT JOIN
		Motivo_Paradas mp WITH (NOLOCK)
			ON mp.Codigo = pq.Codigo
	LEFT JOIN 
		Maquinas maq WITH (NOLOCK)
			ON maq.ID = pq.Maquina_ID
	LEFT JOIN 
		Pavilhao pav WITH (NOLOCK)
			ON pav.ID = maq.ID_Pavilhao
	LEFT JOIN 
		Fabricas fab WITH (NOLOCK)
			ON fab.ID = pav.ID_Fabrica
	LEFT JOIN 
		cte_horarios_setor h
			ON h.cod_setor = maq.ID_Pavilhao
	WHERE 
		maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66)
		AND pav.ID_Fabrica NOT IN (38, 43)
		AND mp.PesoOee = 'Com Peso'
)

SELECT 
	cod_estabelecimento,
	data_apontamento,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	cod_motivo_apontamento,
	des_motivo_apontamento,
	ROUND(SUM(tempo_apontamento), 2) as tempo_apontamento,
	SUM(qtd_pares_perda) as qtd_pares_perda,
	chave_maquina
FROM 
	cte_qualidade
WHERE
	data_apontamento >= CAST(@DataInicioAnalise AS DATE) 
	AND data_apontamento <= CAST(@DataFimAnalise AS DATE)
GROUP BY
	cod_estabelecimento,
	data_apontamento,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	cod_motivo_apontamento,
	des_motivo_apontamento,
	chave_maquina
ORDER BY 
	data_apontamento,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno
