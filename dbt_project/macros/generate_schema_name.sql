-- Use the configured schema name verbatim (STAGING/MARTS/GOLD) instead of
-- dbt's default <target_schema>_<custom_schema> prefixing.
{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}

    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
