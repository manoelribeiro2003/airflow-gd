with cte_performance as (
	select 
		q.id_estabelecimento,
		q.data_hora,
		q.codigo,
		cm.descricao,
		cm.peso_oee,
		q.maquina_id   as id_equipamento,
		maq.nome       as nome_equipamento,
		cs.descricao   as setor,
		cf.descricao   as fabrica,
		q.ciclo,
		q.valor,
		(q.ciclo * q.valor)  as tempo_perda_performance,
		q.efetivo,
		q.turno,
		q.numero_produto,
		q.programa,
		q.documento
	from elipse.silver.oee_fperformance q
	left join elipse.silver.cadastros_motivos cm on q.codigo = cm.codigo and q.id_estabelecimento  = cm.id_estabelecimento 
	left join elipse.silver.cadastros_maquinas maq on q.maquina_id = maq.id and q.id_estabelecimento = maq.id_estabelecimento 
	left join elipse.silver.cadastros_setores cs on maq.id_setor = cs.id and q.id_estabelecimento = cs.id_estabelecimento 
	left join elipse.silver.cadastros_fabricas cf on cf.id = cs.id_fabrica and q.id_estabelecimento = cf.id_estabelecimento 
	where q.data_hora between '{{ params.data_inicio }}' and '{{ params.data_fim }}'
	) 
merge into elipse.gold.oee_fperformance q
using cte_performance o 
on q.id_estabelecimento = o.id_estabelecimento and q.id_equipamento = o.id_equipamento and q.data_hora = o.data_hora
when matched then 
	update set
		id_estabelecimento = o.id_estabelecimento,
		data_hora = o.data_hora,
		codigo = o.codigo,
		descricao = o.descricao,
		peso_oee = o.peso_oee,
		id_equipamento = o.id_equipamento,
		nome_equipamento = o.nome_equipamento,
		setor = o.setor,
		fabrica = o.fabrica,
		ciclo = o.ciclo,
		valor = o.valor,
		tempo_perda_performance = o.tempo_perda_performance,
		efetivo = o.efetivo,
		turno = o.turno,
		numero_produto = o.numero_produto,
		programa = o.programa,
		documento = o.documento,
		data_atualizacao_db = now() - INTERVAL '3 hours'
when not matched by target then
	insert(
		id_estabelecimento,
		data_hora,
		codigo,
		descricao,
		peso_oee,
		id_equipamento,
		nome_equipamento,
		setor,
		fabrica,
		ciclo,
		valor,
		tempo_perda_performance,
		efetivo,
		turno,
		numero_produto,
		programa,
		documento,
		data_atualizacao_db
	)
	values(
		o.id_estabelecimento,
		o.data_hora,
		o.codigo,
		o.descricao,
		o.peso_oee,
		o.id_equipamento,
		o.nome_equipamento,
		o.setor,
		o.fabrica,
		o.ciclo,
		o.valor,
		o.tempo_perda_performance,
		o.efetivo,
		o.turno,
		o.numero_produto,
		o.programa,
		o.documento,
		now() - INTERVAL '3 hours'
	)
	when not matched by source and q.data_hora between '{{ params.data_inicio }}' and '{{ params.data_fim }}' then
	delete;
