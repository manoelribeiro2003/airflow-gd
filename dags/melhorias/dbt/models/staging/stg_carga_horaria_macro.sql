-- Limpeza 1:1 sobre mel_carga_horaria_macro (horas trabalhadas mensais por
-- estabelecimento + macro setor, planilha do Qlik).

select
    estabelecimento,
    area,
    mes,
    ch_mensal
from {{ source('aux', 'mel_carga_horaria_macro') }}
