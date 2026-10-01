-- mel_ganhos_ajuste troca o ganho_previsto da FAP inteira (ADR 0011). Só vale para FAP
-- de tipo sem volume com exatamente uma linha no bronze: com mais linhas o valor da
-- planilha seria somado uma vez por linha, e nos tipos com volume ganho_previsto não
-- entra no R$. FAP do seed que sumiu do bronze também falha (ajuste sem efeito).

select
    aj.numero_fap,
    count(g.id) as linhas_bronze,
    max(g.tipo_melhoria) as tipo_melhoria
from {{ ref('mel_ganhos_ajuste') }} as aj
left join {{ source('bronze', 'mel_ganhos') }} as g
    on aj.numero_fap = g.numero_fap
group by aj.numero_fap
having count(g.id) <> 1
    or max(g.tipo_melhoria) in (
        N'Tempo Ciclo', N'Aglutinação', N'Consumo', N'Troca de Matéria Prima'
    )
