# Volume de produção
O volume de produção é registrado por data, local de produção, produto ...

exemplo do .parquet dos volumes:

|local_producao_cod|produto_cod|produto_cod_com_grade|centro_custo_codtc|reporte_data|Mes|Ano|mesch|volume_producao|
|------------------|-----------|---------------------|------------------|------------|---|---|-----|---------------|
|20030140|2724827|2724827|20030141|2025-01-06 00:00:00.000|1|2025|01/2025|850.0|
|20070160|2724805|2724805|20070211|2025-01-06 00:00:00.000|1|2025|01/2025|1492.0|
|20070070|27248|2724812C5|20070071|2025-01-06 00:00:00.000|1|2025|01/2025|2736.0|
|20070130|2724886|2724886|20070131|2025-01-07 00:00:00.000|1|2025|01/2025|1492.0|
|20030140|2724802|2724802|20030141|2025-01-08 00:00:00.000|1|2025|01/2025|228.0|
|20070070|27248|272481228|20070071|2025-01-08 00:00:00.000|1|2025|01/2025|36.0|
|20070070|27248|2724812C5|20070071|2025-01-09 00:00:00.000|1|2025|01/2025|444.0|
|20030140|2724826|2724826|20030141|2025-01-09 00:00:00.000|1|2025|01/2025|4232.0|
|20030140|2724802|2724802|20030141|2025-01-09 00:00:00.000|1|2025|01/2025|1314.0|

## Objetivo
Criar um pipeline de atualização dos volumes das melhorias via dag do airflow.

## Volume de produção para um produto
- Um produto tem volume por local de produção.
- Um produto tem codigo de 5 digitos.
- Um componente tem codigo de 7 digitos.
- Um produto/componente que tem mais de 7 digitos e tem letras na composição do codigo e o local de produção for `*0070` são codigos de embalagem. Esses produtos são exclusivos do setor `Embalagem*`.
- Um componente é uma peça que vira um produto após sua montagem.
- O volume de produção de um produto é diferente do volume de produção de um componente.
- O volume de produção de um produto/componente pode ser duplicado devido aos locais de produção, quando isso ocorre, deve ser selecionado somente um volume ou deve ser definido o local de produção para pegar o volume.
- Para evitar o problema de duplicação deve-se ter uma tabela com os locais de produção a serem desconsiderados no calculo.


## Volume de produção para uma melhoria
- Uma melhoria tem volume baseado no seu codigo de produto.
- O volume de uma melhoria é calculado somando o volume de um produto/componente por local de produção.
- A chave para calcular um volume é numero_fap, data_fap e produto/componente.
- O range para calcular o volume de uma melhoria é definido pela data_fap, se uma data_fap começa em 2026-05-15, seu volume para 05/2026 é a soma do volume entre 2026-05-15 e 2026-05-31 e o volume para 06/2026 é a soma do volume entre 2026-06-01 e 2026-06-14, ou seja, o volume de uma melhoria deve ser calculado com data_fap + 30 dias. Inicio = data_fap e Fim = data_fap + 30 dias.
- Esse volume deve ser atualizado via dag e deve executar após a dag de atualizar a data da fap.
- O volume deve ser atualizado por range de data, por exemplo, nos ultimos 3 meses, deve ser configuravels via variavel do airflow.
- Só existe volume para melhorias do tipo tempo ciclo, aglutinação, consumo e troca de materia prima.

## Banco de dados
```sql
CREATE TABLE dbengenharia.dbo.mel_volume_real (
	numero_fap varchar(30) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	cod_prod varchar(16) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	mes_ano varchar(10) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	volume int DEFAULT 0 NOT NULL,
	data_inicio date NOT NULL,
	data_fim date NOT NULL,
	CONSTRAINT mel_volume_real_pk PRIMARY KEY (numero_fap, cod_prod, mes_ano)
);

CREATE TABLE dbengenharia.dbo.mel_local_producao_volume_desconsiderados (
	id int IDENTITY(1,1) NOT NULL,
	local_producao varchar(20) COLLATE Latin1_General_100_CI_AS_SC_UTF8 NOT NULL,
	CONSTRAINT mel_local_producao_volume_desconsiderados_pk PRIMARY KEY (id)
);
```
## Fonte dos volumes
Os volumes virão de um arquivo .parquet que é atualizado via qlik saas.
Esse .parquet fica salvo em `https://grendenecombr.sharepoint.com/sites/Dados_Indicadores/Documentos%20Compartilhados%2FArquivos%20Melhorias`

esse arquivo deve ser carregado via graph api e depois injetado no duckdb para então enviar para `dbengenharia.dbo.mel_volume_real`.

O .parquet tem o esquema demostrado no exmplo acima.

## DBT
Devemos atualizar o dbt para usar o volume real em vez do volume estimado.
