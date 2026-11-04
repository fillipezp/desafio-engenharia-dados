
import duckdb
from pathlib import Path

# Localização do banco
raiz_projeto = Path(__file__).resolve().parent.parent
caminho_banco = raiz_projeto / "funil.duckdb"

conexao = duckdb.connect(str(caminho_banco), read_only=True)

try:
    resultado = conexao.execute("""
        SELECT
            COUNT(*) AS total_registros,
            COUNT(DISTINCT event_hash) AS hashes_distintos,
            COUNT(DISTINCT deal_id) AS deals_distintos,
            COUNT(*) - COUNT(DISTINCT deal_id)
                AS atualizacoes_adicionais
        FROM raw.crm_deals
    """).fetchone()

    print("=== AUDITORIA DA CAMADA BRONZE ===")
    print(f"Total armazenado: {resultado[0]}")
    print(f"Hashes distintos: {resultado[1]}")
    print(f"Deals distintos: {resultado[2]}")
    print(f"Atualizações adicionais: {resultado[3]}")

    print("\n=== DEALS COM MAIS VERSÕES ===")

    registros = conexao.execute("""
        SELECT
            deal_id,
            COUNT(*) AS quantidade_versoes
        FROM raw.crm_deals
        GROUP BY deal_id
        HAVING COUNT(*) > 1
        ORDER BY quantidade_versoes DESC, deal_id
        LIMIT 10
    """).fetchall()

    for deal_id, quantidade in registros:
        print(f"{deal_id}: {quantidade} versões")

finally:
    conexao.close()
