-- Período de Análise
DECLARE @DataInicioAnalise DATETIME = GETDATE() - 5;
DECLARE @DataFimAnalise DATETIME = GETDATE();

WITH
cte_familias AS (
	SELECT 
		ID AS cod_familia, 
		Familia AS des_familia, 
		Indice AS des_indice, 
		CASE 
			WHEN 
				ID = 65 THEN 2 WHEN ID = 66 THEN 3 WHEN ID = 67 THEN 1 WHEN ID = 70 THEN 1 WHEN ID = 71 THEN 4 WHEN ID = 73 THEN 1 WHEN ID = 76 
				THEN 1 WHEN ID = 78 THEN 1 WHEN ID = 79 THEN 1 WHEN ID = 80 THEN 1 WHEN ID = 81 THEN 1 WHEN ID = 82 THEN 1 WHEN ID = 83 THEN 1 
				WHEN ID = 84 THEN 1 WHEN ID = 86 THEN 5 WHEN ID = 87 THEN 1 WHEN ID = 115 THEN 3 WHEN ID = 116 THEN 2 WHEN ID = 119 THEN 1 
				WHEN ID = 120 THEN 1 WHEN ID = 121 THEN 1 WHEN ID = 122 THEN 1 WHEN ID = 137 THEN 1 WHEN ID = 138 THEN 1 WHEN ID = 139 THEN 2 
		ELSE 
			NULL 
		END as cod_agg_familia
	FROM 
		Familia_paradas WITH (NOLOCK)
),


cte_familias_agrupadas AS (
    SELECT 
    	* FROM 
    	(VALUES 
    	(1, 'Produção'), 
    	(2, 'Manutenção'), 
    	(3, 'Matrizaria'), 
    	(4, 'Tingimento'), 
    	(5, 'Setup')) AS T (cod_agg_familia, agg_des_familia)
),

-- Busca os horários de cada setor 
cte_horarios_setor AS (
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

cte_setup_lookup AS (
    SELECT 
        ID_Grupo, 
        Descricao AS tp_setup
    FROM (
        SELECT 
            par.ID_Grupo, 
            mp.Descricao,
            ROW_NUMBER() OVER(
                PARTITION BY par.ID_Grupo 
                ORDER BY par.Hora_Inicio ASC
            ) AS rn
        FROM 
            Paradas par WITH (NOLOCK)
        JOIN 
            Motivo_Paradas mp WITH (NOLOCK) ON mp.Codigo = par.Codigo
        WHERE 
            par.ID_Grupo IS NOT NULL
            AND par.Tempo = 1
            AND par.Hora_Inicio <= @DataFimAnalise 
            AND mp.Codigo NOT IN (0, 106, 1614)
    ) AS sub
    WHERE 
        rn = 1 
),

cte_paradas_base AS (
	SELECT par.*,
	case 
		when par.Codigo = 100 and par.ID_Grupo IS NULL then 'Troca de Cor'
		when par.Codigo = 107 and par.ID_Grupo IS NULL then 'Setup Matriz'
		when par.Codigo = 125 and par.ID_Grupo IS NULL then 'Troca de Layout'
		when par.Codigo = 126 and par.ID_Grupo IS NULL then 'Troca Numeração'
		when par.Codigo = 149 and par.ID_Grupo IS NULL then 'Troca de Produto'
		when par.Codigo = 400 and par.ID_Grupo IS NULL then 'Setup Matriz'
		when par.Codigo = 402 and par.ID_Grupo IS NULL then 'Troca de coleção'
		when par.Codigo = 816 and par.ID_Grupo IS NULL AND pav.ID_Fabrica NOT IN (28, 31, 32) then 'Deslocamento de Equipe'
		when par.Codigo = 826 and par.ID_Grupo IS NULL AND pav.ID_Fabrica NOT IN (28, 31, 32) then 'Ligada de Máquina'
		when par.Codigo = 892 and par.ID_Grupo IS NULL then 'Troca de Cor com Limpeza de Bico'
		when par.Codigo = 1701 and par.ID_Grupo IS NULL then 'Troca de Cor com Glitter'
		when par.Codigo = 1728 and par.ID_Grupo IS NULL then 'Setup de Matriz e Cor'
		else COALESCE(setup.tp_setup, '')
	end as tp_setup
	/*, ROW_NUMBER() OVER(PARTITION BY par.ID_Grupo ORDER BY par.Hora_Inicio ASC) AS OrdemNoGrupoParada*/
	FROM 
		Paradas par WITH (NOLOCK)
	LEFT JOIN 
		Motivo_Paradas mot WITH (NOLOCK) ON mot.Codigo = par.Codigo 
	LEFT JOIN 
		Maquinas maq WITH (NOLOCK) ON maq.ID = par.Maquina_ID
	LEFT JOIN 
		Pavilhao pav WITH (NOLOCK) ON maq.ID_Pavilhao = pav.ID
	LEFT JOIN
		cte_setup_lookup setup ON par.ID_Grupo = setup.ID_Grupo
	WHERE 
		par.Hora_Inicio <= @DataFimAnalise 
		AND par.E3TimeStamp >= @DataInicioAnalise
		AND mot.PesoOee = 'Com Peso'
		AND maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66)
		AND pav.ID_Fabrica NOT IN (38, 43)

),

/*cte_grupo_limites AS (
    SELECT 
    	ID_Grupo, 
    	MIN(Hora_Inicio) as inicio_grupo, 
    	MAX(E3TimeStamp) as fim_grupo
    FROM 
    	cte_paradas_base
    WHERE 
    	ID_Grupo IS NOT NULL 
    GROUP BY 
    	ID_Grupo
),*/

cte_eventos_parada AS (
    SELECT 
    	p.Status,
    	p.Maquina_ID, 
    	p.NumeroProduto, 
    	p.Documento,
    	p.Programa,
    	p.Codigo, 
    	p.ID_grupo, 
    	p.tp_setup,
    	maq.ID_Pavilhao as cod_setor,
        p.Hora_Inicio AS ts_inicio_evento,
        p.E3TimeStamp AS ts_fim_evento
    FROM 
    	cte_paradas_base p 
    /*LEFT JOIN 
    	cte_grupo_limites g ON p.ID_Grupo = g.ID_Grupo*/
    LEFT JOIN 
    	Maquinas maq WITH (NOLOCK) on maq.ID = p.Maquina_ID 
    /*WHERE 
    	p.ID_Grupo IS NULL OR p.OrdemNoGrupoParada = 1*/
),

-- Gera os dias para ser gerado uma grade de turnos conforme o horario de inicio e fim do turno do setor
DatasParaAnalisar AS (
    SELECT 
    	CAST(DATEADD(DAY, -1, @DataInicioAnalise) AS DATE) AS Dia 
    	UNION ALL
    	SELECT DATEADD(day, 1, Dia) 
    		FROM DatasParaAnalisar
    	WHERE 
    		Dia < CAST(@DataFimAnalise AS DATE)
),

TurnosGridVirtual AS (
    -- Turno 1 para todos os setores
    SELECT 
    	h.cod_setor, 
    	d.Dia AS data_turno, 
    	1 AS num_turno,
        CAST(
        	CAST(d.Dia AS VARCHAR) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T1 AS VARCHAR) 
        AS DATETIME) AS inicio_turno,
        
        CAST(
	        CAST(d.Dia AS VARCHAR) 
		    + ' ' 
		    + CAST(h.Fim_1_T1 AS VARCHAR) AS DATETIME) AS fim_turno,
		    
		CAST(
        	CAST(d.Dia AS VARCHAR) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T1 AS VARCHAR) 
        AS DATETIME) AS ini_T1,
        
        CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T3 as time) > '00:00:00' AND CAST(h.Fim_1_T3 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T3 AS VARCHAR) 
        AS DATETIME) AS fim_T3
    FROM 
    	DatasParaAnalisar d 
    CROSS JOIN 
    	cte_horarios_setor h 
    UNION ALL
    -- Turno 2 para todos os setores
    SELECT 
    	h.cod_setor, 
    	d.Dia, 
    	2,
        CAST(
        	CAST(
        		CASE 
		            WHEN CAST(h.Ini_1_T2 as time) > '00:00:00' AND CAST(h.Ini_1_T2 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
		        ) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T2 AS VARCHAR) AS DATETIME),
        	
    	CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T2 as time) > '00:00:00' AND CAST(h.Fim_1_T2 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T2 AS VARCHAR) AS DATETIME),         
		    
		CAST(
        	CAST(d.Dia AS VARCHAR) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T1 AS VARCHAR) 
        AS DATETIME) AS ini_T1,
        
        CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T3 as time) > '00:00:00' AND CAST(h.Fim_1_T3 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T3 AS VARCHAR) 
        AS DATETIME) AS fim_T3
    FROM 
    	DatasParaAnalisar d 
    CROSS JOIN 
    	cte_horarios_setor h 
    UNION ALL
    -- Turno 3 para todos os setores
    SELECT 
    	h.cod_setor, 
    	d.Dia, 
    	3,
        CAST(
        	CAST(
	        	CASE
	        		WHEN CAST(h.Ini_1_T3 as time) > '00:00:00' AND CAST(h.Ini_1_T3 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
        	)
        	+ ' ' 
        	+ CAST(h.Ini_1_T3 AS VARCHAR) AS DATETIME),
    	CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T3 as time) > '00:00:00' AND CAST(h.Fim_1_T3 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T3 AS VARCHAR) AS DATETIME),
        CAST(
        	CAST(d.Dia AS VARCHAR) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T1 AS VARCHAR) 
        AS DATETIME) AS ini_T1,
        
        CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T3 as time) > '00:00:00' AND CAST(h.Fim_1_T3 as time) < CAST(h.Ini_1_T1 as time) 
		            THEN DATEADD(day, 1, d.Dia) 
		            ELSE d.Dia 
		            END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T3 AS VARCHAR) 
        AS DATETIME) AS fim_T3
    FROM 
    	DatasParaAnalisar d
    CROSS JOIN 
    	cte_horarios_setor h
),

-- 5. CTE das paradas com o grid de turnos
ParadasSobreTurnos AS (
	SELECT
		'20' AS cod_estabelecimento,
		h.des_setor,
		t.data_turno AS data_parada,
		e.ts_inicio_evento AS ts_inicio_parada,
		e.ts_fim_evento AS ts_fim_parada,
		t.inicio_turno,
		t.fim_turno,		
		t.num_turno AS num_turno,
		e.Maquina_ID AS cod_maquina,
		ma.Nome AS des_nome_maquina,
	    e.NumeroProduto AS cod_produto,
	    e.Documento AS num_documento,
	    e.Programa AS num_programa,
		e.Codigo AS cod_motivo_parada,	
		m.Descricao AS des_motivo_parada,
		CASE 
			WHEN m.Descricao LIKE '%Aguardando%' AND agg_f.agg_des_familia = 'Matrizaria' THEN 'Aguardando Matrizaria' 
			WHEN m.Descricao NOT LIKE '%Aguardando%' AND agg_f.agg_des_familia = 'Matrizaria' THEN 'Reparo Matrizaria' 
			WHEN m.Descricao LIKE '%Aguardando%' AND agg_f.agg_des_familia = 'Manutenção' THEN 'Aguardando Manutenção' 
			WHEN m.Descricao NOT LIKE '%Aguardando%' AND agg_f.agg_des_familia = 'Manutenção' THEN 'Reparo Manutenção' 
		END AS tp_parada,
		CASE 
			WHEN e.tp_setup <> ''
				THEN 'Setup' 
			ELSE 
				agg_f.agg_des_familia 
		END AS des_familia,
		m.PesoOee as des_peso_oee, 
		CASE 
    		WHEN e.ID_Grupo IS NULL AND e.tp_setup <> '' THEN
	        LEFT(
	            CONVERT(
	                VARCHAR(32), 
	                HASHBYTES(
		                'MD5',
	                    CAST(e.Maquina_ID AS VARCHAR(100)) + CAST(e.ts_inicio_evento AS VARCHAR(100))
	                ), 
	                2 
	            ), 
	            8
	        )
    	ELSE 
        	CAST(e.ID_Grupo AS VARCHAR(100))
		END AS cod_grupo_parada,
		e.tp_setup,
		CASE
		    WHEN (e.Codigo IN (107, 454, 1704, 400, 1041, 129) AND e.tp_setup = 'Setup Matriz')
				OR (e.Codigo IN (100, 1707, 1708, 129) AND e.tp_setup = 'Troca de Cor')
				OR (e.Codigo IN (892, 1701))
		    THEN 'Sim'
		    ELSE ''
		END AS bln_motivo_flat,
		DATEDIFF(
			second, 
			CASE 
				WHEN e.ts_inicio_evento > t.inicio_turno 
					THEN e.ts_inicio_evento 
				ELSE t.inicio_turno 
			END, 
			CASE 
				WHEN e.ts_fim_evento < t.fim_turno 
					THEN e.ts_fim_evento 
				ELSE t.fim_turno 
			END) AS tempo_parada,
		CASE WHEN e.Status = 1 OR e.Status = 4 THEN 'Não' ELSE 'Sim' END AS bln_parada_fechada,
		CASE
			WHEN 
				e.ts_inicio_evento >= t.inicio_turno AND e.ts_inicio_evento <= t.fim_turno
			OR
				e.ts_fim_evento >= t.inicio_turno AND e.ts_fim_evento <= t.fim_turno AND e.ts_inicio_evento < t.ini_T1
			OR
				t.num_turno = 1 AND e.ts_inicio_evento < t.inicio_turno AND e.ts_fim_evento > t.fim_turno 
				AND e.ts_inicio_evento < t.ini_T1 AND e.ts_fim_evento > t.fim_T3
			THEN 'Sim' 
			ELSE 'Não' 
		END AS bln_contabiliza_dia, --lógica para separar paradas que se repetem ou não no dia
		CASE
	    	WHEN
	    		e.ts_fim_evento >= t.inicio_turno AND e.ts_fim_evento <= t.fim_turno
		    THEN 'Sim'
	    	ELSE 'Não'
		END AS bln_contabiliza_mes, -- lógica para saber se a quantidade será contabilizada pro mês
		'20' + CAST(e.Maquina_ID AS VARCHAR) AS chave_maquina
	FROM
	    cte_eventos_parada e 
	LEFT JOIN
	    TurnosGridVirtual t
	    	ON 
	    		e.ts_inicio_evento < t.fim_turno 
		    	AND e.ts_fim_evento > t.inicio_turno 
	    		AND e.cod_setor = t.cod_setor
	LEFT JOIN 
		cte_horarios_setor h 
			ON e.cod_setor = h.cod_setor
	LEFT JOIN 
		Maquinas ma WITH (NOLOCK)
			ON ma.ID = e.Maquina_ID
	LEFT JOIN 
		Motivo_Paradas m WITH (NOLOCK) 
			ON m.Codigo = e.Codigo
	LEFT JOIN 
		cte_familias f 
			ON f.cod_familia = m.ID_Familia
	LEFT JOIN 
		cte_familias_agrupadas agg_f 
			ON agg_f.cod_agg_familia = f.cod_agg_familia
)

SELECT
	cod_estabelecimento,
	data_parada,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	cod_motivo_parada,
	des_motivo_parada,
	COUNT(cod_motivo_parada) AS qtd_motivo,
	tp_parada,
	des_familia,
	tp_setup,
	bln_motivo_flat,
	des_peso_oee,
	cod_grupo_parada,
	SUM(tempo_parada) as tempo_parada,
	chave_maquina,
	bln_parada_fechada,
	bln_contabiliza_dia,
	bln_contabiliza_mes
FROM 
	ParadasSobreTurnos 
WHERE 
	data_parada >= CAST(@DataInicioAnalise AS DATE) 
	AND data_parada <= CAST(@DataFimAnalise AS DATE)
	AND cod_motivo_parada = 826
GROUP BY 
	cod_estabelecimento,
	data_parada,
	cod_maquina,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	num_turno,
	cod_motivo_parada,
	des_motivo_parada,
	tp_parada,
	des_familia,
	tp_setup,
	bln_motivo_flat,
	des_peso_oee,
	cod_grupo_parada,
	chave_maquina,
	bln_parada_fechada,
	bln_contabiliza_dia,
	bln_contabiliza_mes
ORDER BY
	data_parada,
	des_nome_maquina,
	cod_produto,
	num_programa,
	num_documento,
	cod_grupo_parada,
	num_turno
OPTION (MAXRECURSION 0);
