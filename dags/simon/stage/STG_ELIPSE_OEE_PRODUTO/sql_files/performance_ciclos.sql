DECLARE @sql NVARCHAR(MAX) = '';  -- Variável para armazenar a consulta final
DECLARE @tableName NVARCHAR(255); -- Variável para armazenar o nome da tabela
DECLARE @ID_Maq NVARCHAR(10);     -- Variável para armazenar o número extraído
DECLARE @filial NVARCHAR(2) ;
DECLARE @datainicial NVARCHAR(20) = GETDATE() - 5;
DECLARE @datafinal NVARCHAR(20) = GETDATE();

SET @filial = '20'

-- Consultar os nomes das tabelas que começam com 'Ciclo'
DECLARE table_cursor CURSOR FOR
SELECT TABLE_NAME
FROM [Elipse].INFORMATION_SCHEMA.TABLES WITH (NOLOCK)
WHERE TABLE_NAME LIKE 'Ciclo %'
AND TABLE_NAME NOT IN ('Ciclo 0', 'Ciclo_Plastisol')
AND TABLE_TYPE = 'BASE TABLE';

-- Abrir o cursor
OPEN table_cursor;

-- Ler a primeira tabela
FETCH NEXT FROM table_cursor INTO @tableName;

-- Loop através das tabelas
WHILE @@FETCH_STATUS = 0
BEGIN
    -- Extrair o número do nome da tabela
    SET @ID_Maq = SUBSTRING(@tableName, 7, LEN(@tableName) - 6);

    -- Adicionar o UNION ALL se a query principal não estiver vazia
    IF LEN(@sql) > 0
    BEGIN
        SET @sql = @sql + ' UNION ALL ';
    END

    -- Adicionar o SELECT com as correções
    SET @sql = @sql +
            'SELECT
				''' + @filial + ''' AS cod_estabelecimento,
                E3TimeStamp AS data_ciclo,
				''' + @ID_MAQ + ''' AS cod_maquina, -- Seleciona o ID da máquina diretamente
				SUBSTRING(Turno, 7, 1) as num_turno,
				NumeroProduto as cod_produto,
				Programa as num_programa,
				Documento as num_documento,
				[Ciclo TI] AS ciclo_padrao,
				[Ciclo Atual] AS ciclo_real,
				Diferenca AS diferenca_ciclo,
				CASE WHEN Diferenca <= 0 THEN Diferenca ELSE 0 END AS ganho_ciclo,
				CASE WHEN Diferenca >= 0 THEN Diferenca ELSE 0 END AS perda_ciclo,
				''' + @filial + ''' + CAST(''' + @ID_MAQ + ''' AS VARCHAR) AS chave_maquina
                
            FROM [Elipse].dbo.' + QUOTENAME(@tableName) + ' WITH(NOLOCK)
            WHERE 
				E3TimeStamp >= ''' + @datainicial + '''  
				'; 

    -- Obter a próxima tabela
    FETCH NEXT FROM table_cursor INTO @tableName;
END

-- Fechar e desalocar o cursor
CLOSE table_cursor;
DEALLOCATE table_cursor;

-- join para pegar a máquina
DECLARE @finalSql NVARCHAR(MAX);
SET @finalSql = N'
    SELECT
		cod_estabelecimento,
		CAST(
			CASE
				WHEN CAST(c.data_ciclo AS TIME) >= ''' + '00:00:00' + ''' AND CAST(c.data_ciclo AS TIME) < hor.Ini_1_T1
				THEN DATEADD(DAY, -1, c.data_ciclo)
				ELSE c.data_ciclo
			END AS DATE
		) AS data_ciclo,
		c.cod_maquina,
		m.Nome as des_nome_maquina,
		c.cod_produto,
		c.num_programa,
		c.num_programa,
		c.num_turno,

		ROUND(AVG(c.ciclo_padrao), 2) AS media_ciclo_padrao,
		ROUND(AVG(c.ciclo_real), 2) AS media_ciclo_real,
		ROUND(AVG(c.diferenca_ciclo), 2) AS media_diferenca_ciclo,
		ROUND(AVG(c.ganho_ciclo), 2) AS media_ganho_ciclo,
		ROUND(AVG(c.perda_ciclo), 2) AS media_perda_ciclo,

		ROUND(SUM(c.ciclo_padrao), 2) AS soma_ciclo_padrao,
		ROUND(SUM(c.ciclo_real), 2) AS soma_ciclo_real,
		ROUND(SUM(c.diferenca_ciclo), 2) AS soma_diferenca_ciclo,
		ROUND(SUM(c.ganho_ciclo), 2) AS soma_ganho_ciclo,
		ROUND(SUM(c.perda_ciclo), 2) AS soma_perda_ciclo,
		c.chave_maquina,
		count(c.data_ciclo) as qtd_ciclos
    FROM
        (' + @sql + ') AS c
    LEFT JOIN 
		Maquinas m WITH (NOLOCK) 
			ON c.cod_maquina = m.ID
	LEFT JOIN
		Pavilhao pav WITH (NOLOCK) 
			ON pav.ID = m.ID_Pavilhao
	LEFT JOIN 
		Fabricas fab WITH (NOLOCK) 
			ON fab.ID = pav.ID_Fabrica
	LEFT JOIN 
		Parametros_Setor param WITH (NOLOCK) 
			ON param.Setor = pav.Pavilhao
	LEFT JOIN 
		Horarios hor WITH (NOLOCK) 
			ON hor.Nome = param.Horario
	WHERE 
		pav.ID NOT IN (52, 69, 74, 59, 50, 36, 70, 66)	
		and pav.ID_Fabrica NOT IN (38, 43)
		AND CAST(
			CASE
				WHEN CAST(c.data_ciclo AS TIME) >= ''' + '00:00:00' + ''' AND CAST(c.data_ciclo AS TIME) < hor.Ini_1_T1
				THEN DATEADD(DAY, -1, c.data_ciclo)
				ELSE c.data_ciclo
			END AS DATE
		) >= CAST(''' + @datainicial + ''' AS DATE) 
		AND CAST(
			CASE
				WHEN CAST(c.data_ciclo AS TIME) >= ''' + '00:00:00' + ''' AND CAST(c.data_ciclo AS TIME) < hor.Ini_1_T1
				THEN DATEADD(DAY, -1, c.data_ciclo)
				ELSE c.data_ciclo
			END AS DATE
		) <= CAST(''' + @datafinal + ''' AS DATE)
	GROUP BY
		c.cod_estabelecimento,
		CAST(
			CASE
				WHEN CAST(c.data_ciclo AS TIME) >= ''' + '00:00:00' + ''' AND CAST(c.data_ciclo AS TIME) < hor.Ini_1_T1
				THEN DATEADD(DAY, -1, c.data_ciclo)
				ELSE c.data_ciclo
			END AS DATE
		),
		c.cod_maquina,
		m.Nome,
		c.cod_produto,
		c.num_programa,
		c.num_documento,
		c.num_turno,
		c.chave_maquina
	ORDER BY
		CAST(
			CASE
				WHEN CAST(c.data_ciclo AS TIME) >= ''' + '00:00:00' + ''' AND CAST(c.data_ciclo AS TIME) < hor.Ini_1_T1
				THEN DATEADD(DAY, -1, c.data_ciclo)
				ELSE c.data_ciclo
			END AS DATE
		),
		m.Nome,
		c.cod_produto,
		c.num_programa,
		c.num_documento,
		c.num_turno
	'

-- Executar a consulta dinâmica final
EXEC sp_executesql @finalSql;

--SELECT @finalSql;
