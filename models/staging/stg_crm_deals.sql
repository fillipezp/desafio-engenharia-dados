
WITH fonte AS (
    SELECT
        event_hash,
        deal_id,
        atualizado_em,
        payload_json,
        ingerido_em
    FROM {{ source('crm', 'deals') }}
),

dados_extraidos AS (
    SELECT
        event_hash,

        json_extract_string(payload_json, '$.id')
            AS deal_id,

        json_extract_string(payload_json, '$.contato_id')
            AS contato_id,

        json_extract_string(payload_json, '$.vendedor')
            AS vendedor,

        json_extract_string(payload_json, '$.etapa')
        AS etapa_original,

        CASE
            WHEN LOWER(TRIM(etapa_original)) = 'won'
                THEN 'ganho'

            WHEN REPLACE(
                LOWER(TRIM(etapa_original)),
                'ç', 'c'
            ) = 'negociacao'
                THEN 'negociação'

            ELSE LOWER(TRIM(etapa_original))
        END AS etapa,

        json_extract_string(payload_json, '$.produto')
            AS produto,

        json_extract_string(payload_json, '$.canal')
            AS canal,

        json_extract_string(payload_json, '$.motivo_perda')
            AS motivo_perda,

        COALESCE(
            json_extract_string(payload_json, '$.valor.amount'),
            json_extract_string(payload_json, '$.valor')
        ) AS valor_original,

        COALESCE(
            json_extract_string(payload_json, '$.valor.currency'),
            json_extract_string(payload_json, '$.moeda')
        ) AS moeda,

        json_extract_string(payload_json, '$.criado_em')
            AS criado_em_original,

        atualizado_em AS atualizado_em_original,

        ingerido_em

    FROM fonte
)

SELECT
    event_hash,
    deal_id,
    contato_id,
    vendedor,
    etapa,
    produto,
    canal,
    motivo_perda,

    TRY_CAST(valor_original AS DECIMAL(18,2))
        AS valor,

    moeda,

    TRY_CAST(criado_em_original AS TIMESTAMPTZ)
        AS criado_em,

    TRY_CAST(atualizado_em_original AS TIMESTAMPTZ)
        AS atualizado_em,

    ingerido_em

FROM dados_extraidos
