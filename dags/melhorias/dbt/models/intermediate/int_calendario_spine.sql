-- Date spine manual. dbt_utils.date_spine gera WITH aninhado
-- (`with rawdata as ( with p as ... )`) que o SQL Server 2008 rejeita
-- (156: Incorrect syntax near 'with'). Aqui: um único nível de WITH com
-- cross-join de dígitos (tally table), 10^4 dias a partir de 2020-01-01
-- (~ano 2047, folga sobre o teto getdate()+1ano). Consumida por dim_calendario.
with digits as (
    select n
    from (values (0), (1), (2), (3), (4), (5), (6), (7), (8), (9)) as d (n)
),

numbers as (
    select d0.n + d1.n * 10 + d2.n * 100 + d3.n * 1000 as offset_dias
    from digits as d0
    cross join digits as d1
    cross join digits as d2
    cross join digits as d3
)

select dateadd(day, offset_dias, cast('2020-01-01' as date)) as date_day
from numbers
where dateadd(day, offset_dias, cast('2020-01-01' as date))
    <= dateadd(year, 1, cast(getdate() as date))
