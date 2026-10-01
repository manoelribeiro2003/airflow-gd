-- dbengenharia.dbo.mel_aprovacao definição

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_aprovacao;

CREATE TABLE dbengenharia.dbo.mel_aprovacao (
	ID int NOT NULL,
	fabrica_melhoria varchar(255) COLLATE Latin1_General_CI_AS NULL,
	filial_melhoria varchar(255) COLLATE Latin1_General_CI_AS NULL,
	origem_melhoria varchar(255) COLLATE Latin1_General_CI_AS NULL,
	macro_setor_nome varchar(255) COLLATE Latin1_General_CI_AS NULL,
	tipo_alteracao varchar(255) COLLATE Latin1_General_CI_AS NULL,
	Author varchar(255) COLLATE Latin1_General_CI_AS NULL,
	Editor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	numero_fap varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	email_aprovador_eng varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	dt_aprovacao_eng datetime NULL,
	comentarios_especialista varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	email_aprovador_producao varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	dt_aprovacao_producao datetime NULL,
	comentarios_aprov_setor varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	status varchar(255) COLLATE Latin1_General_CI_AS NULL,
	nome_quem_aprovou_setor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	nome_quem_aprovou_especialista varchar(255) COLLATE Latin1_General_CI_AS NULL,
	Modified datetime2(3) NULL,
	status_aprov_setor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	status_aprov_especialista varchar(255) COLLATE Latin1_General_CI_AS NULL,
	codigos_produto varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	dt_inicio_fluxo datetime NULL,
	status_aprov_analista varchar(255) COLLATE Latin1_General_CI_AS NULL,
	nome_quem_aprovou_analista varchar(255) COLLATE Latin1_General_CI_AS NULL,
	dt_aprovacao_analista datetime NULL,
	ID_anexo int NULL,
	nome_especialista varchar(255) COLLATE Latin1_General_CI_AS NULL,
	nome_aprovador_setor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	email_analistas varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	email_sup_engenharia varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	dt_fap datetime NULL,
	solicitante varchar(255) COLLATE Latin1_General_CI_AS NULL,
	tipo_melhoria varchar(255) COLLATE Latin1_General_CI_AS NULL,
	setor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	numero_fap_pai varchar(255) COLLATE Latin1_General_CI_AS NULL,
	guid_anexos varchar(255) COLLATE Latin1_General_CI_AS NULL,
	cracha_idealizador int NULL,
	nome_idealizador varchar(255) COLLATE Latin1_General_CI_AS NULL,
	cc_idealizador varchar(255) COLLATE Latin1_General_CI_AS NULL,
	setor_idealizador varchar(255) COLLATE Latin1_General_CI_AS NULL,
	gerente_idealizador varchar(255) COLLATE Latin1_General_CI_AS NULL,
	cargo_idealizador varchar(255) COLLATE Latin1_General_CI_AS NULL,
	tipo_fap varchar(255) COLLATE Latin1_General_CI_AS NULL,
	dt_fap_informada_por varchar(255) COLLATE Latin1_General_CI_AS NULL,
	desc_melhoria varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	investimento real NULL,
	custo_MOD real NULL,
	desc_processo_atual varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	desc_processo_proposto varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	carga_horaria_mes real NULL,
	gerente_melhoria varchar(255) COLLATE Latin1_General_CI_AS NULL,
	Created datetime2(3) NULL,
	comentarios_analista varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	CertificacaoImetro varchar(255) COLLATE Latin1_General_CI_AS NULL,
	status_aprovador_inmetro varchar(255) COLLATE Latin1_General_CI_AS NULL,
	dt_aprovacao_inmetro datetime NULL,
	comentario_aprovador_inmetro varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	nome_quem_aprovou_inmetro varchar(255) COLLATE Latin1_General_CI_AS NULL,
	eh_ganho varchar(255) COLLATE Latin1_General_CI_AS NULL,
	quem_aprovou_gerencia_eng varchar(255) COLLATE Latin1_General_CI_AS NULL,
	status_aprovador_gerencia_eng varchar(255) COLLATE Latin1_General_CI_AS NULL,
	comentarios_aprovador_gerencia_e varchar(MAX) COLLATE Latin1_General_CI_AS NULL,
	dt_aprovacao_gerencia_eng datetime NULL,
	tipo_produto varchar(255) COLLATE Latin1_General_CI_AS NULL,
	CONSTRAINT mel_aprovacao_numero_fap_unique UNIQUE (numero_fap),
	CONSTRAINT mel_aprovacao_pk PRIMARY KEY (ID)
);
 CREATE NONCLUSTERED INDEX mel_aprovacao_Modified_IDX ON dbengenharia.dbo.mel_aprovacao (  Modified ASC  )
	 WITH (  PAD_INDEX = OFF ,FILLFACTOR = 100  ,SORT_IN_TEMPDB = OFF , IGNORE_DUP_KEY = OFF , STATISTICS_NORECOMPUTE = OFF , ONLINE = OFF , ALLOW_ROW_LOCKS = ON , ALLOW_PAGE_LOCKS = ON  )
	 ON [PRIMARY ] ;


-- dbengenharia.dbo.mel_carga_horaria definição

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_carga_horaria;

CREATE TABLE dbengenharia.dbo.mel_carga_horaria (
	id int IDENTITY(1,1) NOT NULL,
	mes date NOT NULL,
	setor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	ch_mensal decimal(18,6) NOT NULL,
	CONSTRAINT mel_carga_horaria_pk PRIMARY KEY (id)
);


-- dbengenharia.dbo.mel_carga_horaria_macro definição (ADR 0006)
-- Carga: SQL gerado por dags/melhorias/scripts/carga_horaria_macro.py

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_carga_horaria_macro;

CREATE TABLE dbengenharia.dbo.mel_carga_horaria_macro (
	estabelecimento varchar(100) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	area varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	mes date NOT NULL,
	ch_mensal decimal(18,6) NOT NULL,
	CONSTRAINT mel_carga_horaria_macro_pk PRIMARY KEY (estabelecimento, area, mes)
);


-- dbengenharia.dbo.mel_custo_funcionario definição

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_custo_funcionario;

CREATE TABLE dbengenharia.dbo.mel_custo_funcionario (
	id int IDENTITY(1,1) NOT NULL,
	mes_ano varchar(20) COLLATE Latin1_General_CI_AS NOT NULL,
	[data] date NOT NULL,
	custo decimal(18,2) NOT NULL,
	estabelecimento varchar(100) COLLATE Latin1_General_CI_AS NOT NULL,
	CONSTRAINT mel_custo_funcionario_pk PRIMARY KEY (id)
);


-- dbengenharia.dbo.mel_ganhos definição

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_ganhos;

CREATE TABLE dbengenharia.dbo.mel_ganhos (
	id int NOT NULL,
	tipo_melhoria varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	filial varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	fabrica varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	setor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	nome_solicitante varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	numero_fap varchar(30) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	dt_fap date NULL,
	cod_prod varchar(MAX) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	preco_mp decimal(18,2) NULL,
	consumo_anterior real NULL,
	consumo_atual real NULL,
	padrao_anterior real NULL,
	padrao_atual real NULL,
	efetivo_anterior real NULL,
	efetivo_atual real NULL,
	tc_anterior real NULL,
	tc_atual real NULL,
	mix real NULL,
	volume_mes_1 real NULL,
	volume_mes_2 real NULL,
	volume_mes_3 real NULL,
	volume_mes_4 real NULL,
	percentual_ganho real NULL,
	custo_par_anterior real NULL,
	custo_par_atual real NULL,
	origem_melhoria varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	macro_setor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	replicavel varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	nome_setor_replicavel varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	is_lacamento_manual bit NULL,
	investimento decimal(18,2) NULL,
	cracha_idealizador int NULL,
	descricao_proc_atual_outras_m varchar(MAX) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	descricao_proc_prop_outras_m varchar(MAX) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	qtde_mo_atual_outras_m real NULL,
	qtde_mo_proposto_outras_m real NULL,
	dt_fap_informada_por varchar(30) COLLATE Latin1_General_CI_AS NULL,
	custo_MOD decimal(18,2) NULL,
	carga_horaria_mes decimal(18,2) NULL,
	peso_ponderado_componente real NULL,
	ganho_previsto decimal(18,2) NULL,
	tipo_alteracao varchar(50) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	id_solicitacao_assinatura int NULL,
	gerente varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	tipo_fap varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	nome_idealizador varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	cc_idealizador varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	gerente_idealizador varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	Created datetime2(3) NULL,
	Modified datetime2(3) NULL,
	replicacao varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	volume_foi_editado bit NULL,
	cargo varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	status_liberacao varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	tipo_produto varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	Author varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	Editor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	-- 1 = linha importada via planilha (DAG MANUAL_MELHORIAS_GANHOS_PLANILHA), id negativo.
	insert_manual bit NOT NULL CONSTRAINT DF_mel_ganhos_insert_manual DEFAULT 0,
	CONSTRAINT PK__mel_ganh__3213E83FFB149B91 PRIMARY KEY (id)
);
 CREATE NONCLUSTERED INDEX mel_ganhos_Modified_IDX ON dbengenharia.dbo.mel_ganhos (  Modified ASC  )
	 WITH (  PAD_INDEX = OFF ,FILLFACTOR = 100  ,SORT_IN_TEMPDB = OFF , IGNORE_DUP_KEY = OFF , STATISTICS_NORECOMPUTE = OFF , ONLINE = OFF , ALLOW_ROW_LOCKS = ON , ALLOW_PAGE_LOCKS = ON  )
	 ON [PRIMARY ] ;


-- dbengenharia.dbo.mel_meta_aderencia definição

-- Drop table

-- DROP TABLE dbengenharia.dbo.mel_meta_aderencia;

CREATE TABLE dbengenharia.dbo.mel_meta_aderencia (
	bimestre varchar(50) COLLATE Latin1_General_CI_AS NULL,
	inicio_bimestre date NULL,
	fim_bimestre date NULL,
	grupo_cargo varchar(100) COLLATE Latin1_General_CI_AS NULL,
	gerente_meta varchar(100) COLLATE Latin1_General_CI_AS NULL,
	atende_somente_um_gerente varchar(30) COLLATE Latin1_General_CI_AS NULL,
	gerente_c_custo varchar(100) COLLATE Latin1_General_CI_AS NULL,
	descricao_situacao varchar(255) COLLATE Latin1_General_CI_AS NULL,
	categoria_situacao varchar(255) COLLATE Latin1_General_CI_AS NULL,
	setor_pnope varchar(255) COLLATE Latin1_General_CI_AS NULL,
	codigo int NULL,
	nome varchar(255) COLLATE Latin1_General_CI_AS NULL,
	[local] varchar(255) COLLATE Latin1_General_CI_AS NULL,
	lotacao varchar(255) COLLATE Latin1_General_CI_AS NULL,
	setor varchar(255) COLLATE Latin1_General_CI_AS NULL,
	c_custo bigint NULL,
	cargo varchar(255) COLLATE Latin1_General_CI_AS NULL,
	turno_lotacao varchar(100) COLLATE Latin1_General_CI_AS NULL,
	turno_historico varchar(100) COLLATE Latin1_General_CI_AS NULL,
	situacao int NULL,
	mdo varchar(100) COLLATE Latin1_General_CI_AS NULL,
	dt_adm date NULL,
	dt_nascimento date NULL,
	sexo varchar(20) COLLATE Latin1_General_CI_AS NULL
);


-- dbengenharia.dbo.mel_volume_real definição
--
-- Volume real de produção atribuído por melhoria (numero_fap + cod_prod + mes_ano),
-- carregado pela DAG SILVER_MELHORIAS_VOLUME_REAL a partir do .parquet do Qlik.
-- PK natural composta (numero_fap, cod_prod, mes_ano): garante a unicidade lógica no
-- banco. Idempotência via DELETE de range + INSERT (a chave reinserida coincide com a
-- apagada, pois data_inicio é determinístico por chave).

-- DROP TABLE dbengenharia.dbo.mel_volume_real;

CREATE TABLE dbengenharia.dbo.mel_volume_real (
	numero_fap varchar(30) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	cod_prod varchar(16) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	mes_ano varchar(10) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	volume int DEFAULT 0 NOT NULL,
	data_inicio date NOT NULL,
	data_fim date NOT NULL,
	CONSTRAINT mel_volume_real_pk PRIMARY KEY (numero_fap, cod_prod, mes_ano)
);



-- dbengenharia.dbo.mel_volume_real_hist definição (ADR 0007)
--
-- Volume real histórico (2021-2025) das planilhas BASE_LANCAMENTO do Qlik, por
-- numero_fap + cod_prod (sem zeros à esquerda) + mes_offset (1 = mês de dt_fap,
-- 2 = mês seguinte). Linha sem código de tipo com volume: cod_prod = 'SEM_CODIGO'
-- (ADR 0013). Carga manual (ADR 0004): SQL gerado por
-- dags/melhorias/scripts/volume_real_hist.py

-- DROP TABLE dbengenharia.dbo.mel_volume_real_hist;

CREATE TABLE dbengenharia.dbo.mel_volume_real_hist (
	numero_fap varchar(30) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	cod_prod varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	mes_offset tinyint NOT NULL,
	volume decimal(18,4) NOT NULL,
	arquivo_origem varchar(100) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	CONSTRAINT mel_volume_real_hist_pk PRIMARY KEY (numero_fap, cod_prod, mes_offset),
	CONSTRAINT mel_volume_real_hist_offset_ck CHECK (mes_offset IN (1, 2))
);

-- dbengenharia.dbo.mel_ganhos_hist definição (ADR 0008)
--
-- Linhas de ganho das FAPs aprovadas sem nenhuma linha em mel_ganhos e das FAPs de
-- mel_ganhos_fonte_planilha (ADR 0013), das planilhas BASE_LANCAMENTO do Qlik. Tipos
-- com ganho por volume: grão da planilha (linha por operação/mix). Demais tipos: uma
-- linha por FAP, ganho_previsto = "Ganho mês R$". Tipos e collation iguais a mel_ganhos
-- (union all em stg_mel_ganhos). Carga manual (ADR 0004): SQL gerado por
-- dags/melhorias/scripts/ganhos_hist.py

-- DROP TABLE dbengenharia.dbo.mel_ganhos_hist;

CREATE TABLE dbengenharia.dbo.mel_ganhos_hist (
	id int NOT NULL,
	numero_fap varchar(30) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	cod_prod varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	dt_fap date NULL,
	tipo_melhoria varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	filial varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	setor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	macro_setor varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	tc_anterior real NULL,
	tc_atual real NULL,
	mix real NULL,
	consumo_anterior real NULL,
	consumo_atual real NULL,
	preco_mp decimal(18,2) NULL,
	custo_par_anterior real NULL,
	custo_par_atual real NULL,
	ganho_previsto decimal(18,2) NULL,
	cracha_idealizador int NULL,
	nome_idealizador varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	gerente_idealizador varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	cargo varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	origem_melhoria varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	replicacao varchar(255) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NULL,
	arquivo_origem varchar(100) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	CONSTRAINT mel_ganhos_hist_pk PRIMARY KEY (id)
);

-- dbengenharia.dbo.mel_local_producao_volume_desconsiderados definição
--
-- Locais de produção a desconsiderar no cálculo de volume (resolve duplicação de
-- volume de um mesmo produto/componente entre locais). Carga manual (ADR 0004).

-- DROP TABLE dbengenharia.dbo.mel_local_producao_volume_desconsiderados;

CREATE TABLE dbengenharia.dbo.mel_local_producao_volume_desconsiderados (
	id int IDENTITY(1,1) NOT NULL,
	local_producao varchar(20) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	CONSTRAINT mel_local_producao_volume_desconsiderados_pk PRIMARY KEY (id)
);
