-- Aplica o remap de gerente (seed mel_gerente_remap, com janela de data) e o lookup
-- de área (seed mel_gerente_area). Grão: (gerente original, inicio_bimestre) vindo da meta.
-- Fall-through: sem match no remap, mantém o gerente original (coalesce).

with origem as (
    select distinct
        gerente_meta as gerente_origem,
        inicio_bimestre
    from {{ ref('stg_meta_aderencia') }}
),

remapeado as (
    select
        o.gerente_origem,
        o.inicio_bimestre,
        coalesce(r.destino, o.gerente_origem) as gerente_ajustado
    from origem as o
    left join {{ ref('mel_gerente_remap') }} as r
        on o.gerente_origem = r.origem
        -- valido_ate nulo = regra sempre vale; senão só antes da data.
        and (r.valido_ate is null or o.inicio_bimestre < r.valido_ate)
)

select
    rm.gerente_origem,
    rm.inicio_bimestre,
    rm.gerente_ajustado,
    a.area
from remapeado as rm
left join {{ ref('mel_gerente_area') }} as a
    on rm.gerente_ajustado = a.gerente
