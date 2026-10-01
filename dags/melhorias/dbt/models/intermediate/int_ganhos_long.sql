-- ADR 0005: materializado como tabela com clustered columnstore (as_columnstore=true
-- default do dbt-sqlserver). Caminho quente: este model é recomputado por fct_ganhos E
-- por int_melhorias_realizado (perf-threshold.md); materializar corta a recomputação dupla.
{{ config(materialized="table") }}

-- Ganhos LONG: uma linha por (FAP, mês 1..4) com ganho_reais convertido (ADR 0003).
-- Espelha base_melhoria do Qlik (docs/qlik/load_data_for_dashboard.md).
--
-- ganho_reais por tipo (regra confirmada, na macro ganho_reais_case):
--   TC/Aglutinação      -> hrs_ganhas_N / ch_mensal * custo  (conversão R$ trabalhista)
--   Consumo/Troca MP    -> g_consumo_N + troca_mp_N          (já em R$)
--   Outros tipos        -> ganho_previsto                    (atribuído ao mês 1)
--
-- Só entram FAPs com status 'Aprovado' em mel_aprovacao (ADR 0003) e com dt_fap: sem
-- data não há competência nem taxa de conversão. dt_fap preenchido NÃO implica
-- aprovação: mel_ganhos.dt_fap vem cru do SharePoint e FAP reprovada, expirada, com
-- falha no fluxo ou cancelada pode ter data (issue #24). O Qlik também excluía esses
-- status. O ganho PREVISTO não tem esse filtro e vive em int_ganhos_previsto.
--
-- Período da conversão = mês de dt_fap (Qlik usa a Data da FAP para os 4 meses).
-- Lookup de carga_horaria/custo_funcionario: int_ganhos_calc.

with aprovadas as (
    -- mel_aprovacao tem uma linha por numero_fap
    select numero_fap
    from {{ ref('stg_mel_aprovacao') }}
    where status = 'Aprovado'
),

calc as (
    -- ch_mensal e custo já vêm resolvidos por mês de dt_fap (int_ganhos_calc)
    select c.*
    from {{ ref('int_ganhos_calc') }} as c
    inner join aprovadas as a
        on c.numero_fap = a.numero_fap
    where c.dt_fap is not null
)

{% for n in range(1, 5) %}
select
    numero_fap,
    id_solicitacao_assinatura,
    tipo_melhoria,
    filial,
    setor,
    macro_setor,
    cracha_idealizador,
    nome_idealizador,
    gerente_idealizador,
    bimestre,
    replicacao,
    {{ n }} as mes_offset,
    dateadd(month, {{ n - 1 }}, dt_fap) as dt_competencia,
    hrs_ganhas_{{ n }} as hrs_ganhas,
    -- ganho em pessoas = horas ganhas / carga horária mensal do setor
    -- (funcionários equivalentes liberados). Mesma guarda do ganho_reais TC.
    case
        when ch_mensal is not null and ch_mensal <> 0
            then hrs_ganhas_{{ n }} / ch_mensal
        else 0
    end as ganho_pessoas,
    {{ ganho_reais_case(n) }} as ganho_reais
from calc
{% if not loop.last %}union all{% endif %}
{% endfor %}
