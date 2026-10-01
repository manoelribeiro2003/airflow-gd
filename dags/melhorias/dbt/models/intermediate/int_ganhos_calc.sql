-- ADR 0009: tabela (clustered columnstore), não view. int_ganhos_long lê este model 4
-- vezes (unpivot) e int_ganhos_previsto mais uma; como view, cada leitura recalculava
-- os joins de volume.
{{ config(materialized="table") }}

-- Cálculo de ganhos (ainda WIDE: meses 1..4 em colunas). O unpivot para long e a
-- conversão R$ acontecem em int_ganhos_long (ADR 0003). Espelha base_melhoria do Qlik.
--
-- Tipos: TC/Aglutinação -> horas ganhas; Consumo -> economia MP; Troca MP -> custo par.
-- Regra Qlik: setor like 'Ting%' cai em troca MP mesmo sendo Consumo.
-- O Qlik aplicava o setor Ting% a qualquer tipo; aqui troca_mp só existe para Consumo
-- e Troca MP, os únicos tipos que o somam no R$ (ganho_reais_case). Em TC/Aglutinação
-- de Ting% o custo par cadastrado é mão de obra por par: o delta repete o ganho das
-- horas e somar contaria duas vezes (ADR 0010, issue #26).
--
-- dt_fap e bimestre vêm de stg_mel_ganhos (mel_ganhos tem dt_fap nativo) -> sem join
-- com aprovacao. carga/custo (taxas do mês de dt_base) saem daqui; ganho_reais (R$) é
-- resolvido no long e no previsto.

with ganhos as (
    select
        *,
        -- chave de mel_volume_real_hist: código sem zeros à esquerda, como o Excel
        -- guarda (0224374 -> 224374; ADR 0007)
        substring(cod_prod, patindex('%[^0]%', cod_prod + '.'), 255) as cod_prod_hist
    from {{ ref('stg_mel_ganhos') }}
),

-- Código acima de 2^53 (16 dígitos, MP do Laboratório F4) passou por double nas
-- planilhas 2021-2023 e perdeu o último dígito ímpar (...0009 -> ...0008). Fallback
-- do join do histórico: mesmo arredondamento aplicado ao código de mel_ganhos. Só
-- entra quando o código exato não casa (2024+ guardam o código exato).
ganhos_chave as (
    select
        *,
        case
            when len(cod_prod_hist) >= 16
                and try_cast(cod_prod_hist as decimal(20, 0)) > 9007199254740992
                then cast(cast(cast(
                    cast(cod_prod_hist as decimal(20, 0)) as float
                ) as decimal(20, 0)) as varchar(30))
        end as cod_prod_hist_float
    from ganhos
),

-- Volume REAL por melhoria. Usado no ganho realizado (ganho_reais). mes_n é o n-ésimo
-- mês a partir de dt_fap: mes_1 = mês de dt_fap, mes_2 = +1 mês, etc. Duas fontes,
-- escolhidas pelo mês de competência (dt_fap + n-1 meses) contra o corte do
-- histórico Qlik (var volume_hist_ate, ADR 0007), sem coalesce entre elas:
--   competência < corte -> mel_volume_real_hist (planilhas do Qlik), por mes_offset = n
--   competência >= corte -> mel_volume_real (DAG), por mes_ano 'MM/YYYY'
-- Só mes_1/mes_2 costumam ter volume (janela real [dt_fap, dt_fap+30d]; o histórico só
-- tem offsets 1 e 2); os demais caem em coalesce 0. FAP de dez/2025: mes_1 do
-- histórico, mes_2 (jan/2026) do mel_volume_real.
-- O volume PREVISTO (volume_mes_1..4 do bronze, estimativa da FAP) alimenta em paralelo
-- o ganho previsto (int_ganhos_previsto), com os mesmos cálculos por tipo.
volume_real as (
    select numero_fap, cod_prod, mes_ano, volume
    from {{ ref('stg_mel_volume_real') }}
),

-- Histórico já pivotado em volume_1..4 por (numero_fap, cod_prod): um join por chave
-- (exata e arredondada) em vez de um por mês: com 8 joins na mesma tabela o otimizador
-- do SQL Server levava minutos só para compilar. A PK (numero_fap, cod_prod, mes_offset) garante 1 linha por mês, e o
-- sum sem linha do mês devolve null, como o left join por mês devolvia (ADR 0009).
volume_real_hist as (
    select
        numero_fap,
        cod_prod,
        {% for n in range(1, 5) %}
        sum(case when mes_offset = {{ n }} then volume end)
            as volume_{{ n }}{{ "," if not loop.last }}
        {% endfor %}
    from {{ ref('stg_mel_volume_real_hist') }}
    group by numero_fap, cod_prod
),

ganhos_vol as (
    select
        g.*,
        {% for n in range(1, 5) %}
        coalesce(g.volume_mes_{{ n }}, 0) as volume_previsto_mes_{{ n }},
        case
            when dateadd(
                month, {{ n - 1 }}, datefromparts(year(g.dt_fap), month(g.dt_fap), 1)
            ) < cast('{{ var("volume_hist_ate") }}' as date)
                then coalesce(vh.volume_{{ n }}, vf.volume_{{ n }}, 0)
            else coalesce(v{{ n }}.volume, 0)
        end as volume_real_mes_{{ n }}{{ "," if not loop.last }}
        {% endfor %}
    from ganhos_chave as g
    {% for n in range(1, 5) %}
    left join volume_real as v{{ n }}
        on v{{ n }}.numero_fap = g.numero_fap
        and v{{ n }}.cod_prod = g.cod_prod
        and v{{ n }}.mes_ano = format(dateadd(month, {{ n - 1 }}, g.dt_fap), 'MM/yyyy')
    {% endfor %}
    left join volume_real_hist as vh
        on vh.numero_fap = g.numero_fap
        and vh.cod_prod = g.cod_prod_hist
    left join volume_real_hist as vf
        on vf.numero_fap = g.numero_fap
        and vf.cod_prod = g.cod_prod_hist_float
),

componentes as (
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
        dt_fap,
        -- Data-base do PREVISTO: dt_fap só é preenchida em FAP aprovada
        -- (SILVER_MELHORIAS_DATA_FAP/update_fap.sql), mas o previsto existe desde o
        -- cadastro. Sem dt_fap cai no created do bronze, que cobre 100% das linhas e
        -- serve de competência para o lookup de carga_horaria/custo_funcionario.
        coalesce(dt_fap, cast(created as date)) as dt_base,
        bimestre,
        replicacao,
        ganho_previsto,
        -- flag de classe: só Tempo Ciclo e Aglutinação contam como tempo de ciclo
        case
            when tipo_melhoria in (N'Tempo Ciclo', N'Aglutinação') then 1 else 0
        end as eh_tempo_ciclo,
        {% set variantes = [
            ('', 'volume_real_mes_'),
            ('_previsto', 'volume_previsto_mes_')
        ] %}
        {% for sufixo, volume in variantes %}
        {% set loop_variante = loop %}
        {% for n in range(1, 5) %}
        -- mês {{ n }}{{ ' (previsto)' if sufixo }}
        case
            when tipo_melhoria in (N'Tempo Ciclo', N'Aglutinação')
                then (tc_anterior - tc_atual) * (mix / 100.0) * {{ volume }}{{ n }} / 60.0
            else 0
        end as hrs_ganhas{{ sufixo }}_{{ n }},
        case
            when tipo_melhoria = 'Consumo' and setor not like 'Ting%'
                then (consumo_anterior - consumo_atual) * (mix / 100.0)
                    * preco_mp * {{ volume }}{{ n }}
            else 0
        end as g_consumo{{ sufixo }}_{{ n }},
        case
            when tipo_melhoria = N'Troca de Matéria Prima'
                or (tipo_melhoria = 'Consumo' and setor like 'Ting%')
                then (custo_par_anterior - custo_par_atual) * (mix / 100.0)
                    * {{ volume }}{{ n }}
            else 0
        end as troca_mp{{ sufixo }}_{{ n }}{{ "," if not (loop.last and loop_variante.last) }}
        {% endfor %}
        {% endfor %}
    from ganhos_vol
),

-- Taxas de conversão hrs -> pessoas/R$ (carga_horaria, custo_funcionario) do mês de
-- dt_base, resolvidas aqui uma vez para os dois consumidores: int_ganhos_long
-- (realizado, dt_fap não nulo -> dt_base = dt_fap) e int_ganhos_previsto.
--
-- Carga horária (ADR 0006):
--   dt_base < volume_hist_ate -> só macro (filial, macro_setor, mês), igual ao Qlik
--   dt_base >= corte          -> setor; nula ou 0 cai no macro
carga as (
    select
        setor,
        year(mes) as ano,
        month(mes) as mes_num,
        ch_mensal
    from {{ ref('stg_carga_horaria') }}
),

carga_macro as (
    select
        estabelecimento,
        area,
        year(mes) as ano,
        month(mes) as mes_num,
        ch_mensal
    from {{ ref('stg_carga_horaria_macro') }}
),

custo as (
    select
        estabelecimento,
        year(dt_competencia) as ano,
        month(dt_competencia) as mes_num,
        custo
    from {{ ref('stg_custo_funcionario') }}
)

select
    c.*,
    case
        when c.dt_base < cast('{{ var("volume_hist_ate") }}' as date)
            then chm.ch_mensal
        else coalesce(nullif(ch.ch_mensal, 0), chm.ch_mensal)
    end as ch_mensal,
    cu.custo
from componentes as c
-- COLLATE DATABASE_DEFAULT: mel_ganhos (setor/filial) e Latin1_General_CI_AS;
-- carga/custo (planilha/VBA) sao UTF8. Sem isto o join de string estoura collation.
left join carga as ch
    on c.setor collate database_default = ch.setor collate database_default
    and year(c.dt_base) = ch.ano
    and month(c.dt_base) = ch.mes_num
left join carga_macro as chm
    on c.filial collate database_default = chm.estabelecimento collate database_default
    and c.macro_setor collate database_default = chm.area collate database_default
    and year(c.dt_base) = chm.ano
    and month(c.dt_base) = chm.mes_num
left join custo as cu
    on c.filial collate database_default = cu.estabelecimento collate database_default
    and year(c.dt_base) = cu.ano
    and month(c.dt_base) = cu.mes_num
