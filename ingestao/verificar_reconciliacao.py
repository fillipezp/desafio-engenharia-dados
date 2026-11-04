
import duckdb
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
banco = raiz / "funil.duckdb"

conexao = duckdb.connect(str(banco), read_only=True)

try:
    resultado = conexao.execute("""
        WITH pagamentos AS (
            SELECT
                deal_id,
                COUNT(*) AS qtd_matriculas_pagas,
                SUM(valor_pago) AS total_pago
            FROM main.stg_erp_matriculas
            WHERE status_pagamento = 'pago'
              AND deal_id IS NOT NULL
            GROUP BY deal_id
        )

        SELECT
            C.etapa,

            COUNT(*) AS total_deals,

            COUNT(*) FILTER (
                WHERE P.deal_id IS NOT NULL
            ) AS deals_com_pagamento,

            COUNT(*) FILTER (
                WHERE P.deal_id IS NULL
            ) AS deals_sem_pagamento,

            COALESCE(SUM(P.qtd_matriculas_pagas), 0)
                AS matriculas_pagas,

            COALESCE(SUM(P.total_pago), 0)
                AS valor_pago

        FROM main.int_deals_atual C

        LEFT JOIN pagamentos P
            ON P.deal_id = C.deal_id

        GROUP BY C.etapa
        ORDER BY C.etapa
    """).fetchall()

    print("=== RECONCILIACAO CRM X ERP ===")

    for linha in resultado:
        etapa, total, com_pgto, sem_pgto, matriculas, valor = linha

        print(
            f"{etapa}: "
            f"{total} deals | "
            f"{com_pgto} com pagamento | "
            f"{sem_pgto} sem pagamento | "
            f"{matriculas} matrículas pagas | "
            f"R$ {valor}"
        )


    print("\n=== PAGAMENTOS SEM VÍNCULO COM CRM ===")

    registros = conexao.execute("""
        SELECT
            E.matricula_id,
            E.deal_id,
            E.status_pagamento,
            E.valor_pago

        FROM main.stg_erp_matriculas E

        LEFT JOIN main.int_deals_atual C
            ON C.deal_id = E.deal_id

        WHERE E.status_pagamento = 'pago'
        AND C.deal_id IS NULL

        ORDER BY E.matricula_id
    """).fetchall()

    total_sem_vinculo = 0

    for matricula_id, deal_id, status, valor in registros:
        print(
            f"Matrícula: {matricula_id} | "
            f"Deal: {deal_id} | "
            f"Valor: R$ {valor}"
        )

        total_sem_vinculo += valor or 0

    print(f"\nTotal sem vínculo: R$ {total_sem_vinculo}")


finally:
    conexao.close()
