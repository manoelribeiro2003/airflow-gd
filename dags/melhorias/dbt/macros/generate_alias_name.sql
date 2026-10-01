{#
    Prefixa toda relação criada pelo dbt (models/views + seeds) com `mel_`.
    Regra do projeto: todas as tabelas têm prefixo `mel_`. Guarda contra
    duplo-prefixo (seeds já nascem `mel_*`). ref()/source() não mudam: resolvem
    pelo node name, não pelo alias.
#}
{% macro generate_alias_name(custom_alias_name=none, node=none) -%}
    {%- if custom_alias_name -%}
        {%- set base = custom_alias_name | trim -%}
    {%- elif node.version -%}
        {%- set base = node.name ~ "_v" ~ (node.version | replace(".", "_")) -%}
    {%- else -%}
        {%- set base = node.name -%}
    {%- endif -%}
    {%- if base.startswith('mel_') -%}
        {{ base }}
    {%- else -%}
        mel_{{ base }}
    {%- endif -%}
{%- endmacro %}
