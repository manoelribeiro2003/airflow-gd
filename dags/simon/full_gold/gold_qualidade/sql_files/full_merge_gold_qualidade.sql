with cte_qualidade as (
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
	q.pares_batida,
	(q.ciclo * q.valor) / q.pares_batida     as tempo_perda_qualidade,
	q.efetivo,
	q.turno,
	q.numero_produto,
	q.programa,
	q.documento,
	q.maquina_id_origem,
	maq2.nome    as nome_equipamento_origem
from elipse.silver.oee_fqualidade q
left join elipse.silver.cadastros_motivos cm on q.codigo = cm.codigo and q.id_estabelecimento  = cm.id_estabelecimento 
left join elipse.silver.cadastros_maquinas maq on q.maquina_id = maq.id and q.id_estabelecimento = maq.id_estabelecimento 
left join elipse.silver.cadastros_setores cs on maq.id_setor = cs.id and q.id_estabelecimento = cs.id_estabelecimento 
left join elipse.silver.cadastros_fabricas cf on cf.id = cs.id_fabrica and q.id_estabelecimento = cf.id_estabelecimento 
left join elipse.silver.cadastros_maquinas maq2 on q.maquina_id_origem = maq2.id and q.id_estabelecimento = maq2.id_estabelecimento
where q.data_hora between '{{ params.data_inicio }}' and '{{ params.data_fim }}'
)
merge into elipse.gold.oee_fqualidade q
using cte_qualidade o 
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
		pares_batida = o.pares_batida,
		tempo_perda_qualidade = o.tempo_perda_qualidade,
		efetivo = o.efetivo,
		turno = o.turno,
		numero_produto = o.numero_produto,
		programa = o.programa,
		documento = o.documento,
		maquina_id_origem = o.maquina_id_origem,
		nome_equipamento_origem = o.nome_equipamento_origem,
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
		pares_batida,
		tempo_perda_qualidade,
		efetivo,
		turno,
		numero_produto,
		programa,
		documento,
		maquina_id_origem,
		nome_equipamento_origem,
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
		o.pares_batida,
		o.tempo_perda_qualidade,
		o.efetivo,
		o.turno,
		o.numero_produto,
		o.programa,
		o.documento,
		o.maquina_id_origem,
		o.nome_equipamento_origem,
		now() - INTERVAL '3 hours'
	)
	when not matched by source and q.data_hora between '{{ params.data_inicio }}' and '{{ params.data_fim }}' then
	delete;
