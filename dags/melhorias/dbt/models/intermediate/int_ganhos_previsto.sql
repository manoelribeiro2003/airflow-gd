-- Ganho PREVISTO por FAP (1 linha/numero_fap), em R$.
--
-- Mesma regra de conversão do ganho realizado (macro ganho_reais_case), mudando só a
-- fonte de volume: aqui entra o volume estimado no cadastro da FAP
-- (mel_ganhos.volume_mes_1..4), não o volume real apurado.
--
-- Diferença estrutural para int_ganhos_long: o previsto NÃO depende de status nem de
-- dt_fap. Ele é a estimativa feita no cadastro, então existe para FAP reprovada,
-- cancelada, expirada ou ainda em andamento. Por isso este model não filtra por
-- dt_fap e usa dt_base (dt_fap com fallback para created) só como competência do
-- lookup de carga_horaria/custo_funcionario, necessário na conversão TC/Aglutinação.
--
-- Grão de entrada = componente (uma linha por Id/cod_prod da FAP); o sum() colapsa
-- para FAP, igual ao que fct_ganhos faz no caminho realizado.

with calc as (
    -- ch_mensal e custo já vêm resolvidos por mês de dt_base (int_ganhos_calc)
    select * from {{ ref('int_ganhos_calc') }}
),

por_mes as (
    select
        numero_fap,
        {% for n in range(1, 5) %}
        {{ ganho_reais_case(n, '_previsto') }} as mes_{{ n }}{{ "," if not loop.last }}
        {% endfor %}
    from calc
    -- mel_ganhos tem linhas de cadastro abortado (numero_fap e todo o resto NULL). O
    -- caminho realizado as descarta de graca via dt_fap; aqui nao ha esse filtro, entao
    -- sem isto o group by devolve uma linha de FAP NULL. Mesmo guard de int_fap_resultado.
    where numero_fap is not null
)

select
    numero_fap,
    sum(mes_1) as ganho_reais_previsto_mes_1,
    sum(mes_1 + mes_2 + mes_3 + mes_4) as ganho_reais_previsto_quadrimestre
from por_mes
group by numero_fap
