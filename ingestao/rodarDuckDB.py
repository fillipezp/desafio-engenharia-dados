import duckdb
from pathlib import Path
import pandas



# Localização do banco
raiz_projeto = Path(__file__).resolve().parent.parent
caminho_banco = raiz_projeto / "funil.duckdb"

# Conecta ao banco (ou cria em memória)
conexao = duckdb.connect(str(caminho_banco), read_only=True)

# Roda o seu SELECT e já traz formatado em DataFrame do Pandas (se tiver instalado)
df = conexao.execute("SELECT * FROM raw.crm_deals LIMIT 10").fetchdf()
print(df)