MERGE INTO {{params.DB}}.silver.oee_fparadas p
USING {{params.DB}}.silver.temp_paradas o
ON (p.id = o."Id" and p.id_estabelecimento = o.id_estabelecimento)
WHEN MATCHED AND (
    p.maquina_id IS DISTINCT FROM o."Maquina_ID" or 
    p.codigo IS DISTINCT FROM o."Codigo" OR
    p.data_hora_inicio IS DISTINCT FROM o."Hora_Inicio" OR
    p.data_hora_fim is null OR
    (p.data_hora_fim is not null and p.data_hora_fim IS DISTINCT FROM o."E3TimeStamp") or
    p.tempo IS DISTINCT FROM o.tempo OR
    p.turno IS DISTINCT FROM o."Turno" OR
    p.status IS DISTINCT FROM o."Status" OR
    p.programa IS DISTINCT FROM o."Programa" OR
    p.documento IS DISTINCT FROM o."Documento" OR
    p.numero_produto IS DISTINCT FROM o."NumeroProduto" OR
    p.efetivo::TEXT IS DISTINCT FROM o."Efetivo"::TEXT OR
    p.id_grupo IS DISTINCT FROM o."ID_Grupo" OR
    p.ref_matriz IS DISTINCT FROM o."Ref_Matriz" OR
    p.ferramental IS DISTINCT FROM o."Ferramental" OR
		p.cracha_operador IS DISTINCT FROM o."Cracha_Operador" OR
		p.cracha_preparador IS DISTINCT FROM o."Cracha_Preparador" OR
		p.cracha_lider IS DISTINCT FROM o."Cracha_Lider"  OR
		p.cracha_apoio IS DISTINCT FROM o."Cracha_Apoio"
)THEN
	UPDATE SET
        maquina_id = o."Maquina_ID",
        codigo = o."Codigo",
        data_hora_inicio = o."Hora_Inicio",
				data_hora_fim = o."E3TimeStamp",
        --data_hora_fim = CASE WHEN o."Status" = 1 then null else o."E3TimeStamp" END,
        tempo = o.tempo,
        turno = o."Turno",
        status = o."Status",
        programa = o."Programa",
        documento = o."Documento",
        numero_produto = o."NumeroProduto",
        efetivo = o."Efetivo",
        id_grupo = o."ID_Grupo",
        ref_matriz = o."Ref_Matriz",
        ferramental = o."Ferramental",
				cracha_operador = o."Cracha_Operador",
			  cracha_preparador = o."Cracha_Preparador",
			  cracha_lider = o."Cracha_Lider", 
				cracha_apoio = o."Cracha_Apoio",
        data_atualizacao_db = now() - INTERVAL '3 hours'
WHEN NOT MATCHED BY TARGET THEN
    INSERT (
	    	id_estabelecimento,
	    	id,
	    	maquina_id, 
	    	codigo,
	    	data_hora_inicio,
	    	data_hora_fim,
	    	tempo,
	    	turno,
	    	status,
	    	programa,
	    	documento,
	    	numero_produto,
	    	efetivo,
	    	id_grupo,
	    	ref_matriz,
	    	ferramental,
				cracha_operador,
			  cracha_preparador,
			  cracha_lider,
				cracha_apoio,
	    	data_atualizacao_db
	    	)
    VALUES (
	    	o.id_estabelecimento, 
	    	o."Id", 
	    	o."Maquina_ID",
	    	o."Codigo",
	    	o."Hora_Inicio",
				o."E3TimeStamp",
	    	--CASE WHEN o."Status" = 1 then null else o."E3TimeStamp" END,
	    	o.tempo,
	    	o."Turno",
	    	o."Status",
	    	o."Programa",
	    	o."Documento",
	    	o."NumeroProduto",
	    	o."Efetivo",
	    	o."ID_Grupo",
	    	o."Ref_Matriz",
	    	o."Ferramental",
				o."Cracha_Operador",
			  o."Cracha_Preparador",
			  o."Cracha_Lider",
				o."Cracha_Apoio",
	    	now() - INTERVAL '3 hours'
    	)
WHEN NOT MATCHED BY SOURCE AND (data_hora_inicio between '{{ params.hora_inicio }}' and '{{ params.hora_fim }}' OR
data_hora_fim between '{{ params.hora_inicio }}' and '{{ params.hora_fim }}' OR
(data_hora_fim < '{{ params.hora_inicio }}' and data_hora_fim > '{{ params.hora_fim }}')) THEN
    DELETE;


drop table {{params.DB}}.silver.temp_paradas;