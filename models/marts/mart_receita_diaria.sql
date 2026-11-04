
{{ config(materialized='table') }}

SELECT
    CAST(data_matricula AS DATE) AS data,
    COUNT(*) AS quantidade_matriculas_pagas,
    SUM(valor_pago) AS receita_confirmada

FROM {{ ref('stg_erp_matriculas') }}

WHERE status_pagamento = 'pago'
  AND data_matricula IS NOT NULL
  AND valor_pago IS NOT NULL

GROUP BY
    CAST(data_matricula AS DATE)
