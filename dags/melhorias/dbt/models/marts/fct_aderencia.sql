-- ADR 0005: tabela com clustered columnstore. Fato unico de meta x realizado.
{{ config(materialized="table") }}

-- Fato de aderencia (roster completo): meta (CENTRAL) x realizado de melhorias.
-- Grao: (bimestre, cracha idealizador). Inclui nao-elegiveis (elegivel=0) para
-- servir tambem de roster; realizado vem por left join.

with meta as (
    select
        bimestre,
        inicio_bimestre,
        fim_bimestre,
        gerente_meta,
        codigo as cracha_idealizador,
        nome,
        cargo,
        grupo_cargo,
        qtde as meta_qtde,
        elegivel
    from {{ ref('stg_meta_aderencia') }}
),

realizado as (
    select * from {{ ref('int_melhorias_realizado') }}
)

select
    m.bimestre,
    m.inicio_bimestre,
    m.fim_bimestre,
    m.gerente_meta,
    m.cracha_idealizador,
    concat(trim(m.bimestre), '|', cast(m.cracha_idealizador as varchar(20)))
        collate database_default as sk_idealizador,
    m.nome,
    m.cargo,
    m.grupo_cargo,
    m.meta_qtde,
    coalesce(r.qtde_melhorias, 0) as realizado_qtde,
    coalesce(r.ganho_total, 0) as ganho_total,
    case
        when m.elegivel = 1
            and m.meta_qtde > 0
            and coalesce(r.qtde_melhorias, 0) >= m.meta_qtde
            then cast(1 as bit)
        else cast(0 as bit)
    end as atingiu_meta,
    m.elegivel
from meta as m
left join realizado as r
    on m.bimestre = r.bimestre
    and m.cracha_idealizador = r.cracha_idealizador
