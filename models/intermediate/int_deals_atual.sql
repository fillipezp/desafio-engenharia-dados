
{{ config(materialized='view') }}

WITH historico AS (

    SELECT
        event_hash,
        deal_id,
        contato_id,
        vendedor,
        etapa,
        --etapa_original,
        produto,
        canal,
        motivo_perda,
        valor,
        moeda,
        criado_em,
        atualizado_em,
        ingerido_em

    FROM {{ ref('stg_crm_deals') }}

),

versoes_ordenadas AS (

    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY deal_id
            ORDER BY
                atualizado_em DESC,
                event_hash DESC
        ) AS numero_versao

    FROM historico

)

SELECT
    event_hash,
    deal_id,
    contato_id,
    vendedor,
    etapa,
    --etapa_original,
    produto,
    canal,
    motivo_perda,
    valor,
    moeda,
    criado_em,
    atualizado_em,
    ingerido_em

FROM versoes_ordenadas

WHERE numero_versao = 1
