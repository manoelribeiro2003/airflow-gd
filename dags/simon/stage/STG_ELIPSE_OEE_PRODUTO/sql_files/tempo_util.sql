-- Período de Análise
DECLARE @DataInicioAnalise DATETIME = GETDATE() - 5;
DECLARE @DataFimAnalise DATETIME = GETDATE();

WITH 
--CTEs de Lookup e Filtro Inicial
HorariosSetor AS (
	SELECT
		pav.ID AS cod_setor,
		hor.Ini_1_T1, hor.Fim_1_T1,
		hor.Ini_1_T2, hor.Fim_1_T2,
		hor.Ini_1_T3, hor.Fim_1_T3
	FROM 
		Pavilhao pav WITH (NOLOCK)
	LEFT JOIN 
		Parametros_Setor param WITH (NOLOCK)
			ON param.Setor = pav.Pavilhao
	LEFT JOIN 
		Horarios hor WITH (NOLOCK)
			ON hor.Nome = param.Horario
	WHERE pav.ID NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
),

cte_produtos_filtrados AS (
	SELECT 
		prod.ID,
		prod.ID_Maq,
		maq.Nome,
		maq.ID_Pavilhao as cod_setor,
		prod.NumeroProduto,
		prod.DataInicio,
		COALESCE(prod.DataFim, GETDATE()) AS DataFim,
		prod.DataFim as DataFim_Original
		--prod.Efetivo
	FROM 
		Produtos AS prod WITH (NOLOCK)
	LEFT JOIN 
		Maquinas AS maq WITH (NOLOCK) ON maq.ID = prod.ID_Maq
	LEFT JOIN 
		Pavilhao pav WITH (NOLOCK) ON maq.ID_Pavilhao = pav.ID
	WHERE 
		prod.DataInicio <= @DataFimAnalise 
		AND COALESCE(prod.DataFim, GETDATE()) >= @DataInicioAnalise
		AND maq.ID_Pavilhao NOT IN (52, 69, 74, 59, 50, 36, 70, 66, 62)
		AND pav.ID_Fabrica NOT IN (38, 43)
),

cte_paradas_sem_peso AS ( --filtrando apenas paradas sem peso no periodo
	select 
		par.*
	from 
		Paradas par WITH (NOLOCK)
	left join 
		Motivo_Paradas mp WITH (NOLOCK)
			on mp.Codigo = par.Codigo
	where
		mp.PesoOEE = 'Sem Peso'
		and par.Hora_Inicio <= @DataFimAnalise
		and par.E3TimeStamp >= @DataInicioAnalise
),

cte_duplicadas_a_excluir AS (  --excluindo produtos duplicados
	SELECT 
		p.ID
	FROM 
		cte_produtos_filtrados AS p
	JOIN (
		SELECT ID_Maq, NumeroProduto,
    	CAST(DataInicio AS DATETIME2(0)) AS DataInicioAgrupada,
    	COUNT(*) AS Quantidade
    	FROM
		    Produtos WITH (NOLOCK)
		GROUP BY ID_Maq, NumeroProduto, CAST(DataInicio AS DATETIME2(0))
		HAVING COUNT(*) > 1
	) AS dup 
		ON p.ID_Maq = dup.ID_Maq
		AND p.NumeroProduto = dup.NumeroProduto
		AND CAST(p.DataInicio AS DATETIME2(0)) = dup.DataInicioAgrupada
	WHERE 
		p.DataFim_Original IS NULL
),

-- Produtos Válidos para Análise
cte_produtos_validos AS (
    SELECT *
    FROM cte_produtos_filtrados
    WHERE ID NOT IN (SELECT ID FROM cte_duplicadas_a_excluir)
),

-- Passo 2: Construção da Grade de Turnos Dinâmica
DatasParaAnalisar AS (
    SELECT CAST(DATEADD(DAY, -1, @DataInicioAnalise) AS DATE) AS Dia 
    UNION ALL
    SELECT DATEADD(day, 1, Dia) FROM DatasParaAnalisar WHERE Dia < CAST(@DataFimAnalise AS DATE)
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
		    + CAST(h.Fim_1_T1 AS VARCHAR) AS DATETIME) AS fim_turno
    FROM 
    	DatasParaAnalisar d 
    CROSS JOIN 
    	HorariosSetor h
    UNION ALL
    -- Turno 2 para todos os setores
    SELECT 
    	h.cod_setor, 
    	d.Dia, 
    	2,
        CAST(
        	CAST(d.Dia AS VARCHAR) 
        	+ ' ' 
        	+ CAST(h.Ini_1_T2 AS VARCHAR) AS DATETIME),
    	CAST(
    		CAST(
	            CASE 
	            WHEN CAST(h.Fim_1_T2 AS TIME) < CAST(h.Ini_1_T2 AS TIME) 					--caso o horario do fim do turno seja menor que o inicio, significa que o fim é em outro dia
	            	THEN 
	            		DATEADD(day, 1, d.Dia) 
	            	ELSE 
	            		d.Dia 
	            	END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T2 AS VARCHAR) AS DATETIME)
    FROM 
    	DatasParaAnalisar d 
    CROSS JOIN 
    	HorariosSetor h
    UNION ALL
    -- Turno 3 para todos os setores
    SELECT 
    	h.cod_setor, 
    	d.Dia, 
    	3,
        CAST(
        	CAST(
	        	CASE
	        		WHEN h.Ini_1_T3 = '00:57:01'
	        		THEN
	        			DATEADD(day, 1, d.Dia)
	        		ELSE
	        			d.Dia
	        		END AS VARCHAR
        	)
        	+ ' ' 
        	+ CAST(h.Ini_1_T3 AS VARCHAR) AS DATETIME),
    	CAST(
    		CAST(
	            CASE 
		            WHEN CAST(h.Fim_1_T3 AS TIME) < CAST(h.Ini_1_T3 AS TIME) OR h.Ini_1_T3 = '00:57:01' --caso o horario do fim do turno seja menor que o inicio, significa que o fim é em outro dia. caso seja 3º turno das outras fabricas alem da 3, o 3 turno é no outro dia
	            	THEN 
	            		DATEADD(day, 1, d.Dia) 
	            	ELSE 
	            		d.Dia 
	            	END AS VARCHAR
	            ) 
            + ' ' 
            + CAST(h.Fim_1_T3 AS VARCHAR) AS DATETIME)
    FROM 
    	DatasParaAnalisar d 
    CROSS JOIN 
    	HorariosSetor h
),


cte_tempo_produto_parada AS( --aloca as paradas dentro da programacao do produto, respeitando a data inicio e fim do produto
	select 
		prod.ID_Maq as id_maquina,
		prod.Nome as des_maquina,
		prod.cod_setor,
		prod.NumeroProduto as cod_produto,
		prod.DataInicio as inicio_produto,
		prod.DataFim as fim_produto,
		CASE WHEN par.Hora_Inicio < prod.DataInicio THEN prod.DataInicio ELSE par.Hora_Inicio END as inicio_parada,
		CASE WHEN par.E3TimeStamp > prod.DataFim THEN prod.DataFim ELSE par.E3TimeStamp END as fim_parada
	from 
		cte_produtos_validos prod
	left join 
		cte_paradas_sem_peso par
			on par.Maquina_ID = prod.ID_Maq
			and par.Hora_Inicio <= prod.DataFim
			and par.E3TimeStamp >= prod.DataInicio
),

agg_cte_tempo_calendario_por_turno as (
	SELECT
        p.ID_Maq as id_maquina,
        p.Nome as des_maquina,
        p.NumeroProduto as cod_produto,
        t.data_turno,
        t.cod_setor,
        t.num_turno,
        SUM(DATEDIFF(
			SECOND, 
			CASE WHEN p.DataInicio > t.inicio_turno THEN p.DataInicio ELSE t.inicio_turno END,
			CASE WHEN p.DataFim < t.fim_turno THEN p.DataFim ELSE t.fim_turno END
		)) AS tempo_calendario
    FROM
        cte_produtos_validos p
    JOIN
        TurnosGridVirtual t ON p.DataInicio < t.fim_turno 
                           AND p.DataFim > t.inicio_turno
                           AND p.cod_setor = t.cod_setor
    GROUP BY 
    	p.ID_Maq,
        p.Nome,
        p.NumeroProduto,
        t.data_turno,
        t.cod_setor,
        t.num_turno
),

agg_cte_tempo_sem_peso_por_turno as (
	SELECT
        p.id_maquina,
        p.des_maquina,
        p.cod_produto,
        t.data_turno,
        t.cod_setor,
        t.num_turno,
        SUM(DATEDIFF(
			SECOND, 
			CASE WHEN p.inicio_parada > t.inicio_turno THEN p.inicio_parada ELSE t.inicio_turno END,
			CASE WHEN p.fim_parada < t.fim_turno THEN p.fim_parada ELSE t.fim_turno END
		)) AS tempo_sem_peso
    FROM
        cte_tempo_produto_parada p
    JOIN
        TurnosGridVirtual t ON p.inicio_parada < t.fim_turno 
                           AND p.fim_parada > t.inicio_turno
                           AND p.cod_setor = t.cod_setor
    GROUP BY 
    	p.id_maquina,
        p.des_maquina,
        p.cod_produto,
        t.data_turno,
        t.cod_setor,
        t.num_turno
)

select 
	'20' as cod_estabelecimento,
	cal.data_turno as data_produto,
	cal.id_maquina as cod_maquina,
    cal.des_maquina as des_nome_maquina,
    cal.cod_produto,
    cal.num_turno,
    cal.tempo_calendario,
	COALESCE(par.tempo_sem_peso, 0) as tempo_sem_peso,
	CASE WHEN COALESCE(par.tempo_sem_peso, 0) > cal.tempo_calendario THEN 0 ELSE (cal.tempo_calendario - COALESCE(par.tempo_sem_peso, 0)) END as tempo_util,
	(cal.tempo_calendario - COALESCE(par.tempo_sem_peso, 0)) as tempo_util_neg,
	'20' + CAST(cal.id_maquina AS VARCHAR) AS chave_maquina
from 
	agg_cte_tempo_calendario_por_turno cal
left join
	agg_cte_tempo_sem_peso_por_turno par
		on par.cod_produto = cal.cod_produto
		and par.id_maquina = cal.id_maquina
        and par.des_maquina = cal.des_maquina
        --and par.qtd_efetivo = cal.qtd_efetivo
        and par.data_turno = cal.data_turno
        and par.num_turno = cal.num_turno
where cal.data_turno >= CAST(@DataInicioAnalise AS DATE)
order by cal.data_turno, cal.des_maquina, cal.cod_produto, cal.num_turno asc 

OPTION (MAXRECURSION 0);
