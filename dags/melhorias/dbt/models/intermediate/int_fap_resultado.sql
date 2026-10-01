-- Classificação Ganho/Perda por FAP (grão: 1 linha por numero_fap). Define se a FAP
-- conta como melhoria realizada (só 'Ganho' conta a qtde no int_melhorias_realizado).
--
-- Regra confirmada (validada 100% vs validar-resultado-fap.csv). tipo_melhoria e
-- tipo_fap são constantes por FAP; os deltas variam entre linhas (produtos) da mesma
-- FAP, por isso agrega por SUM antes de comparar. Precedência do CASE:
--   1. Tempo Ciclo / Aglutinação -> sum(tc_atual) - sum(tc_anterior) <= 0
--   2. Consumo (não Tingimento)  -> sum(consumo_atual) - sum(consumo_anterior) <= 0
--   3. Troca MP OU Tingimento    -> sum(custo_par_atual) - sum(custo_par_anterior) <= 0
--   4. demais tipos              -> sum(ganho_previsto) >= 0
-- Tingimento vem de tipo_fap = 'Tingimento' (coluna distinta de tipo_melhoria).

with agg as (
    select
        numero_fap,
        max(tipo_melhoria) as tipo_melhoria,
        max(tipo_fap) as tipo_fap,
        sum(tc_atual) - sum(tc_anterior) as d_tc,
        sum(consumo_atual) - sum(consumo_anterior) as d_consumo,
        sum(custo_par_atual) - sum(custo_par_anterior) as d_custo_par,
        sum(coalesce(ganho_previsto, 0)) as ganho_previsto
    from {{ ref('stg_mel_ganhos') }}
    where numero_fap is not null
    group by numero_fap
)

select
    numero_fap,
    case
        when tipo_melhoria in (N'Tempo Ciclo', N'Aglutinação')
            then case when d_tc <= 0 then 'Ganho' else 'Perda' end
        when tipo_melhoria = N'Consumo' and (tipo_fap is null or tipo_fap <> N'Tingimento')
            then case when d_consumo <= 0 then 'Ganho' else 'Perda' end
        when tipo_melhoria = N'Troca de Matéria Prima' or tipo_fap = N'Tingimento'
            then case when d_custo_par <= 0 then 'Ganho' else 'Perda' end
        else case when ganho_previsto >= 0 then 'Ganho' else 'Perda' end
    end as resultado_fap
from agg
