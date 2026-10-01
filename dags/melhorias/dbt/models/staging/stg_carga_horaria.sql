-- Limpeza 1:1 sobre mel_carga_horaria (horas trabalhadas mensais por setor).

select
    mes,
    setor,
    ch_mensal
from {{ source('aux', 'mel_carga_horaria') }}
