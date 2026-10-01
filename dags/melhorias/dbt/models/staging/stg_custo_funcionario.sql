-- Limpeza 1:1 sobre mel_custo_funcionario (custo mensal por estabelecimento).

select
    mes_ano,
    data as dt_competencia,
    estabelecimento,
    custo
from {{ source('aux', 'mel_custo_funcionario') }}
