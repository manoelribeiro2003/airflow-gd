create table if not exists ferramental.sku (
	log_id uuid not null,
	sku text not null,
	descricao text null,
	status text null,
	qtdcif float4 null,
	fabrica text null,
	ferramenta text null,
	qtd_estoque float4 null,
	loaded_at timestamptz not null default current_timestamp
)
