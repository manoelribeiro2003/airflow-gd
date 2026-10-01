-- troca_mp só existe para Consumo e Troca MP, os tipos que o somam no R$
-- (ganho_reais_case). Em TC/Aglutinação de setor Ting% o delta de custo par repete o
-- ganho das horas; calcular de novo deixaria o valor à toa no model e convidaria a
-- somar duas vezes (ADR 0010, issue #26).

select
    numero_fap,
    tipo_melhoria,
    setor
from {{ ref('int_ganhos_calc') }}
where tipo_melhoria not in (N'Consumo', N'Troca de Matéria Prima')
    and (
        troca_mp_1 <> 0 or troca_mp_2 <> 0 or troca_mp_3 <> 0 or troca_mp_4 <> 0
        or troca_mp_previsto_1 <> 0 or troca_mp_previsto_2 <> 0
        or troca_mp_previsto_3 <> 0 or troca_mp_previsto_4 <> 0
    )
