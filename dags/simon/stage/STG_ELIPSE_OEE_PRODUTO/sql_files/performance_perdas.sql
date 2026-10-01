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

cte_perdas_performace AS (
	SELECT
		'20' AS cod_estabelecimento,
		perf.E3TimeStamp,
		CAST(
			CASE
				WHEN CAST(perf.E3TimeStamp AS TIME) >= '00:00:00' AND CAST(perf.E3TimeStamp AS TIME) < h.Ini_1_T1
				THEN DATEADD(DAY, -1, perf.E3TimeStamp)
				ELSE perf.E3TimeStamp
			END
		AS DATE) AS data_perda,
		perf.Maquina_ID as cod_maquina,
		m.Nome as des_nome_maquina,
		perf.NumeroProduto as cod_produto,
		perf.Programa as num_programa,
		perf.Documento as num_documento,
		SUBSTRING(perf.Turno, 7, 1) as num_turno,
		mp.Descricao as des_perda,
		perf.Valor as qtd_perda,
		perf.Valor * perf.Ciclo as tempo_perda,
		'20' + CAST(perf.Maquina_ID AS VARCHAR) AS chave_maquina
	FROM
		Perdas_Performance perf WITH (NOLOCK)
	LEFT JOIN 
		Motivo_Paradas mp WITH (NOLOCK)
			ON mp.Codigo = perf.Codigo
	LEFT JOIN
		Maquinas m WITH (NOLOCK)
			ON m.ID = perf.Maquina_ID
	LEFT JOIN
		Pavilhao pav WITH (NOLOCK)
			ON pav.ID = m.ID_Pavilhao
	LEFT JOIN 
		Fabricas f WITH (NOLOCK)
			ON f.ID = pav.ID_Fabrica
	LEFT JOIN 
	cte_horarios_setor h
		ON h.cod_setor = m.ID_Pavilhao
	WHERE
		pav.ID NOT IN (52, 69, 74, 59, 50, 36, 70, 66)
		AND f.ID NOT IN (38, 43)
		AND perf.E3TimeStamp >= @DataInicioAnalise AND perf.E3TimeStamp <= @DataFimAnalise
)

SELECT 
	cod_estabelecimento,
	data_perda,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	des_perda,
	SUM(qtd_perda) as qtd_perda,
	ROUND(SUM(tempo_perda), 2) as tempo_perda,
	chave_maquina
FROM
	cte_perdas_performace
WHERE 
	data_perda >= CAST(@DataInicioAnalise AS DATE)
	AND data_perda <= CAST(@DataFimAnalise AS DATE)
GROUP BY 
	cod_estabelecimento,
	data_perda,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	des_perda,
	chave_maquina
ORDER BY
	data_perda,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno
