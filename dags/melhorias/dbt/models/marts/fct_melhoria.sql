-- ADR 0005: tabela com clustered columnstore. Extração instantânea no refresh do
-- Power BI import.
{{ config(materialized="table") }}

-- Fato resumo por FAP (1 linha/numero_fap): aprovacao (status, tipo_produto,
-- tipo_melhoria) + ganho agregado (R$, replicacao, origem_melhoria). Roster completo:
-- todas as FAPs, todos os status; ganho por left join (0/null quando sem ganho).
--
-- ganho_reais = soma de int_ganhos_long por FAP (todos meses/componentes = R$ canônico).
-- ganho_reais_previsto_* = int_ganhos_previsto (mesmo cálculo com o volume estimado no
-- cadastro, mel_ganhos.volume_mes_1..4). Independe de status e de dt_fap: existe também
-- para FAP reprovada, cancelada, expirada ou em andamento — ao contrário do ganho_reais,
-- que só é computado para FAP aprovada (int_ganhos_long).
-- replicacao/origem_melhoria vêm de mel_ganhos, constantes por FAP (max determinístico).

with aprov as (
    select
        numero_fap,
        status,
        tipo_produto,
        tipo_melhoria,
        bimestre,
        cracha_idealizador
    from {{ ref('stg_mel_aprovacao') }}
),

ganho_val as (
    select
        numero_fap,
        sum(ganho_reais) as ganho_reais
    from {{ ref('int_ganhos_long') }}
    group by numero_fap
),

ganho_prev as (
    select
        numero_fap,
        ganho_reais_previsto_mes_1,
        ganho_reais_previsto_quadrimestre
    from {{ ref('int_ganhos_previsto') }}
),

ganho_attr as (
    select
        numero_fap,
        max(replicacao) as replicacao,
        max(origem_melhoria) as origem_melhoria
    from {{ ref('stg_mel_ganhos') }}
    group by numero_fap
),

resultado as (
    select
        numero_fap,
        resultado_fap
    from {{ ref('int_fap_resultado') }}
)

select
    a.bimestre,
    -- chave de relação Power BI (bimestre|crachá) -> dim_idealizador (ponte)
    concat(trim(a.bimestre), '|', cast(a.cracha_idealizador as varchar(20)))
        collate database_default as sk_idealizador,
    a.numero_fap,
    a.status,
    a.tipo_produto,
    a.tipo_melhoria,
    ga.replicacao,
    coalesce(gv.ganho_reais, 0) as ganho_reais,
    coalesce(gp.ganho_reais_previsto_mes_1, 0) as ganho_reais_previsto_mes_1,
    coalesce(gp.ganho_reais_previsto_quadrimestre, 0) as ganho_reais_previsto_quadrimestre,
    ga.origem_melhoria,
    rs.resultado_fap
from aprov as a
-- COLLATE DATABASE_DEFAULT: mel_aprovacao é UTF8, mel_ganhos é Latin1; join de string
-- entre as duas origens estoura conflito de collation sem isto (ver README/Collation).
left join ganho_val as gv
    on a.numero_fap collate database_default = gv.numero_fap collate database_default
left join ganho_attr as ga
    on a.numero_fap collate database_default = ga.numero_fap collate database_default
left join ganho_prev as gp
    on a.numero_fap collate database_default = gp.numero_fap collate database_default
left join resultado as rs
    on a.numero_fap collate database_default = rs.numero_fap collate database_default
