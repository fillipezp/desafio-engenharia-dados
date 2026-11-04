
WITH fonte AS (

    SELECT
        *
    FROM {{ source('erp', 'matriculas') }}

),

dados_tratados AS (

    SELECT
        NULLIF(TRIM(matricula_id), '')
            AS matricula_id,

        NULLIF(TRIM(deal_id), '')
            AS deal_id,

        LOWER(NULLIF(TRIM(email_aluno), ''))
            AS email_aluno,

        NULLIF(TRIM(curso_codigo), '')
            AS curso_codigo,

        data_matricula
            AS data_matricula_original,

        TRY_STRPTIME(
            TRIM(data_matricula),
            '%d/%m/%Y %H:%M'
        ) AS data_matricula,

        status_pagamento
            AS status_pagamento_original,

        LOWER(TRIM(status_pagamento))
            AS status_pagamento,

        valor_pago
            AS valor_pago_original,

        TRY_CAST(
            REPLACE(
                REPLACE(TRIM(valor_pago), '.', ''),
                ',', '.'
            )
            AS DECIMAL(18,2)
        ) AS valor_pago

    FROM fonte

)

SELECT *
FROM dados_tratados
