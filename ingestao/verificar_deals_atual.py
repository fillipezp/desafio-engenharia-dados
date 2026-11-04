
import duckdb
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
banco = raiz / "funil.duckdb"

conexao = duckdb.connect(str(banco), read_only=True)

try:
    print("=== ESTADO ATUAL DAS OPORTUNIDADES ===")

    resultado = conexao.execute("""
        SELECT
            COUNT(*) AS total_deals,
            COUNT(DISTINCT deal_id) AS deals_distintos,
            COUNT(*) FILTER (
                WHERE deal_id IS NULL
            ) AS ids_nulos
        FROM main.int_deals_atual
    """).fetchone()

    print(f"Total de deals: {resultado[0]}")
    print(f"Deals distintos: {resultado[1]}")
    print(f"IDs nulos: {resultado[2]}")

    print("\n=== FUNIL ATUAL ===")

    etapas = conexao.execute("""
        SELECT
            etapa,
            COUNT(*) AS quantidade,
            SUM(valor) AS valor_total
        FROM main.int_deals_atual
        GROUP BY etapa
        ORDER BY quantidade DESC
    """).fetchall()

    for etapa, quantidade, valor in etapas:
        print(
            f"{etapa}: {quantidade} deals | "
            f"Valor: R$ {valor or 0}"
        )

    print("\n=== EMPATES DE ATUALIZAÇÃO ===")

    empates = conexao.execute("""
        SELECT
            COUNT(*) AS grupos_com_empate
        FROM (
            SELECT
                deal_id,
                atualizado_em,
                COUNT(*) AS quantidade
            FROM main.stg_crm_deals
            GROUP BY deal_id, atualizado_em
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    print(f"Grupos com mesmo deal e timestamp: {empates}")

finally:
    conexao.close()
