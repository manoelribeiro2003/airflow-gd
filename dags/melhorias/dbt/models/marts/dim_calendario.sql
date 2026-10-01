-- Calendário diário. Link dos fatos por dt_fap / dt_competencia (ADR 0003).
-- Range: spine amplo (datas extras numa dim são inofensivas); o Power BI fatia.
-- Bimestre derivado: ceil(mes/2).

select
    cast(date_day as date) as data,
    year(date_day) as ano,
    month(date_day) as mes,
    day(date_day) as dia,
    (month(date_day) + 1) / 2 as bimestre_num,
    -- bimestre canônico 'mes1-mes2/ano' (ex. jan-fev/2026), igual aos fatos
    b.bimestre + '/' + cast(year(date_day) as varchar(4)) as bimestre
from {{ ref('int_calendario_spine') }} as dias
left join {{ ref('mel_bimestre') }} as b
    on month(dias.date_day) = b.mes
