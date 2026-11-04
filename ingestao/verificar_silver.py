
import duckdb
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
banco = raiz / "funil.duckdb"

conexao = duckdb.connect(str(banco), read_only=True)

try:
    print("=== AUDITORIA SILVER - CRM ===")

    resultado = conexao.execute("""
        SELECT
            COUNT(*) AS total_registros,
            COUNT(DISTINCT deal_id) AS deals_distintos,
            COUNT(*) FILTER (
                WHERE deal_id IS NULL
            ) AS ids_nulos,
            COUNT(*) FILTER (
                WHERE atualizado_em IS NULL
            ) AS datas_invalidas,
            COUNT(*) FILTER (
                WHERE criado_em IS NULL
            ) AS criacoes_invalidas,
            COUNT(*) FILTER (
                WHERE valor IS NULL
            ) AS valores_nulos
        FROM main.stg_crm_deals
    """).fetchone()

    campos = [
        "Total de registros",
        "Deals distintos",
        "IDs nulos",
        "Datas de atualização inválidas",
        "Datas de criação inválidas",
        "Valores nulos"
    ]

    for nome, valor in zip(campos, resultado):
        print(f"{nome}: {valor}")

    print("\n=== REGISTROS POR ETAPA ===")

    etapas = conexao.execute("""
        SELECT
            etapa,
            COUNT(*) AS quantidade
        FROM main.stg_crm_deals
        GROUP BY etapa
        ORDER BY quantidade DESC
    """).fetchall()

    for etapa, quantidade in etapas:
        print(f"{etapa}: {quantidade}")

finally:
    conexao.close()
