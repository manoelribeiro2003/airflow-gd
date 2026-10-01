-- Dimensão de idealizador. Grão (bimestre, crachá): atributos variam por bimestre
-- (gerente, cargo, elegibilidade). Fonte: roster da meta (stg_meta_aderencia).

select
    bimestre,
    codigo as cracha_idealizador,
    concat(trim(bimestre), '|', cast(codigo as varchar(20))) collate database_default
        as sk_idealizador,
    nome as nome_idealizador,
    cargo,
    grupo_cargo,
    setor,
    gerente_meta,
    elegivel
from {{ ref('stg_meta_aderencia') }}
