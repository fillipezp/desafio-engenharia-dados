
import duckdb
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
banco = raiz / "funil.duckdb"

conexao = duckdb.connect(str(banco), read_only=True)

try:
    print("=== AUDITORIA GOLD ===")

    resultado = conexao.execute("""
        SELECT
            SUM(quantidade_deals),
            SUM(valor_total)
        FROM main.mart_funil
    """).fetchone()

    print(f"Total de deals no funil: {resultado[0]}")
    print(f"Valor total do funil: R$ {resultado[1]}")

    resultado = conexao.execute("""
        SELECT
            SUM(quantidade_matriculas_pagas),
            SUM(receita_confirmada)
        FROM main.mart_receita_diaria
    """).fetchone()

    print(f"Matrículas pagas: {resultado[0]}")
    print(f"Receita confirmada: R$ {resultado[1]}")

    print("\n=== RECEITA POR DIA ===")

    registros = conexao.execute("""
        SELECT
            data,
            quantidade_matriculas_pagas,
            receita_confirmada
        FROM main.mart_receita_diaria
        ORDER BY data
    """).fetchall()

    for data, quantidade, receita in registros:
        print(
            f"{data} | "
            f"{quantidade} matrículas | "
            f"R$ {receita}"
        )

finally:
    conexao.close()
