merge into elipse.silver.oee_fqualidade as q
using elipse.silver.temp_qualidade as o
on (q.data_hora = o."E3TimeStamp" and q.maquina_id = o."Maquina_ID" and q.id_estabelecimento = o.id_estabelecimento)
when matched and (
	q.id_estabelecimento is distinct from o.id_estabelecimento or
	q.data_hora is distinct from o."E3TimeStamp" or
	q.codigo is distinct from o."Codigo" or
	q.valor is distinct from o."Valor" or
	q.maquina_id is distinct from o."Maquina_ID" or
	q.ciclo is distinct from o."Ciclo" or
	q.pares_batida is distinct from o."Pares_Batida" or
	q.turno is distinct from o."Turno" or
	q.numero_produto is distinct from o."NumeroProduto" or
	q.programa is distinct from o."Programa" or
	q.documento is distinct from o."Documento" or
	q.efetivo is distinct from o."Efetivo" or
	q.maquina_id_origem is distinct from o."Maquina_ID_Origem"
)then
	update set
		id_estabelecimento = o.id_estabelecimento,
		data_hora = o."E3TimeStamp",
		codigo = o."Codigo",
		valor = o."Valor",
		maquina_id = o."Maquina_ID",
		ciclo = o."Ciclo",
		pares_batida = o."Pares_Batida",
		turno = o."Turno",
		numero_produto = o."NumeroProduto",
		programa = o."Programa",
		documento = o."Documento",
		efetivo = o."Efetivo",
		maquina_id_origem = o."Maquina_ID_Origem",
		data_atualizacao_db = now() - INTERVAL '3 hours'
when not matched by target then
	insert(
		id_estabelecimento,
		data_hora,
		codigo,
		valor,
		maquina_id,
		ciclo,
		pares_batida,
		turno,
		numero_produto,
		programa,
		documento,
		efetivo,
		maquina_id_origem,
		data_atualizacao_db
	)
	values(
		o.id_estabelecimento,
		o."E3TimeStamp",
		o."Codigo",
		o."Valor",
		o."Maquina_ID",
		o."Ciclo",
		o."Pares_Batida",
		o."Turno",
		o."NumeroProduto",
		o."Programa",
		o."Documento",
		o."Efetivo",
		o."Maquina_ID_Origem",
		now() - INTERVAL '3 hours'
	)
when not matched by source and q.data_hora between %(data_inicio)s and %(data_fim)s then
	delete;


drop table elipse.silver.temp_qualidade;