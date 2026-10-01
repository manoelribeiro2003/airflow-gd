-- Dimensão de gerente já remapeado + área (int_gerente_remap).

select distinct
    gerente_ajustado as gerente,
    area
from {{ ref('int_gerente_remap') }}
