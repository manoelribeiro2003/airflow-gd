{#
    Regra canônica de conversão do ganho para R$, por tipo de melhoria (ADR 0003).

    Fica em macro porque é usada em dois caminhos com fontes de volume diferentes:
    int_ganhos_long (volume real, sufixo vazio) e int_ganhos_previsto (volume
    previsto da FAP, sufixo _previsto). A regra é a mesma; só mudam as colunas de
    componente. Duplicar o case abriria espaço para as duas versões divergirem.

    Espera no escopo: tipo_melhoria, ganho_previsto, ch_mensal, custo e os
    componentes hrs_ganhas{sufixo}_{n}, g_consumo{sufixo}_{n}, troca_mp{sufixo}_{n}.

    O ramo é escolhido só por tipo_melhoria, igual a coluna R$ Mês da planilha
    BASE_LANCAMENTO. A regra de setor Ting% (Consumo vira delta de custo par) já está
    dentro de g_consumo/troca_mp em int_ganhos_calc; repetir o setor aqui mandava tipos
    fora de volume (Manutenção, GGF...) de setor Ting% para g_consumo + troca_mp, que
    é nulo para eles, e zerava o ganho_previsto.
#}
{% macro ganho_reais_case(n, sufixo="") %}
case
    when tipo_melhoria in (N'Tempo Ciclo', N'Aglutinação')
        then case
            when ch_mensal is not null and ch_mensal <> 0
                then hrs_ganhas{{ sufixo }}_{{ n }} / ch_mensal * custo
            else 0
        end
    when tipo_melhoria in (N'Consumo', N'Troca de Matéria Prima')
        then g_consumo{{ sufixo }}_{{ n }} + troca_mp{{ sufixo }}_{{ n }}
    -- Só existe ganho_previsto para o primeiro mês (1).
    else case when {{ n }} = 1 then coalesce(ganho_previsto, 0) else 0 end
end
{% endmacro %}
