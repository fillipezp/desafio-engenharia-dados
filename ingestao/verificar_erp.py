
import duckdb
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
banco = raiz / "funil.duckdb"

conexao = duckdb.connect(str(banco), read_only=True)

try:
    resultado = conexao.execute("""
        SELECT
            COUNT(*) AS total_matriculas,
            COUNT(DISTINCT matricula_id) AS ids_distintos,
            COUNT(*) FILTER (
                WHERE deal_id IS NULL
            ) AS sem_deal_id,
            COUNT(*) FILTER (
                WHERE data_matricula IS NULL
            ) AS datas_invalidas,
            COUNT(*) FILTER (
                WHERE valor_pago IS NULL
            ) AS valores_invalidos
        FROM main.stg_erp_matriculas
    """).fetchone()

    print("=== AUDITORIA ERP ===")
    print(f"Total de matrículas: {resultado[0]}")
    print(f"IDs distintos: {resultado[1]}")
    print(f"Sem deal_id: {resultado[2]}")
    print(f"Datas inválidas: {resultado[3]}")
    print(f"Valores inválidos: {resultado[4]}")

    print("\n=== PAGAMENTOS POR STATUS ===")

    pagamentos = conexao.execute("""
        SELECT
            status_pagamento,
            COUNT(*) AS quantidade,
            SUM(valor_pago) AS valor_total
        FROM main.stg_erp_matriculas
        GROUP BY status_pagamento
        ORDER BY status_pagamento
    """).fetchall()

    for status, quantidade, valor in pagamentos:
        print(
            f"{status}: {quantidade} matrículas | "
            f"Valor: R$ {valor}"
        )

finally:
    conexao.close()
