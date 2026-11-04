
{{ config(materialized='table') }}

SELECT
    etapa,
    COUNT(*) AS quantidade_deals,
    SUM(COALESCE(valor, 0)) AS valor_total,
    COUNT(*) FILTER (
        WHERE valor IS NOT NULL
    ) AS deals_com_valor

FROM {{ ref('int_deals_atual') }}

GROUP BY etapa
