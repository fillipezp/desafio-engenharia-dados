
import os
import json
import time
import hashlib
import logging
from pathlib import Path

import requests
import duckdb


# ==========================================
# CONFIGURAÇÕES
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "funil.duckdb"
PASTA_LOGS = RAIZ / "logs"

URL_API = "http://localhost:8000/deals"
TOKEN = os.getenv("CRM_API_TOKEN")

TAMANHO_PAGINA = 100
MAX_TENTATIVAS = 5


# ==========================================
# CONFIGURAÇÃO DOS LOGS
# ==========================================

PASTA_LOGS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            PASTA_LOGS / "ingestao_crm.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ingestao_crm")


# ==========================================
# CONSULTA À API
# ==========================================

def buscar_pagina(pagina):
    """Busca uma página com retentativas para falhas temporárias."""

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    parametros = {
        "page": pagina,
        "page_size": TAMANHO_PAGINA
    }

    for tentativa in range(1, MAX_TENTATIVAS + 1):

        try:
            resposta = requests.get(
                URL_API,
                headers=headers,
                params=parametros,
                timeout=15
            )

            codigo = resposta.status_code

            # Erros temporários
            if codigo == 429 or 500 <= codigo < 600:

                if tentativa == MAX_TENTATIVAS:
                    resposta.raise_for_status()

                if codigo == 429:
                    try:
                        espera = float(
                            resposta.headers.get("Retry-After", "1")
                        )
                    except ValueError:
                        espera = 2 ** (tentativa - 1)
                else:
                    espera = 2 ** (tentativa - 1)

                espera = max(0, espera)

                logger.warning(
                    "Página %s | HTTP %s | Tentativa %s/%s | "
                    "Aguardando %.1fs",
                    pagina, codigo, tentativa,
                    MAX_TENTATIVAS, espera
                )

                time.sleep(espera)
                continue

            # Erros definitivos
            resposta.raise_for_status()

            dados = resposta.json()

            if not isinstance(dados.get("data"), list):
                raise ValueError(
                    f"Resposta inválida na página {pagina}"
                )

            return dados

        except (requests.Timeout, requests.ConnectionError) as erro:

            if tentativa == MAX_TENTATIVAS:
                raise RuntimeError(
                    f"Falha de conexão na página {pagina}"
                ) from erro

            espera = 2 ** (tentativa - 1)

            logger.warning(
                "Página %s | Falha de conexão | "
                "Tentativa %s/%s | Aguardando %ss",
                pagina, tentativa, MAX_TENTATIVAS, espera
            )

            time.sleep(espera)

    raise RuntimeError(
        f"Não foi possível consultar a página {pagina}"
    )


# ==========================================
# EXTRAÇÃO COMPLETA
# ==========================================

def extrair_crm():

    pagina = 1
    registros = []
    paginas_visitadas = set()

    logger.info("Iniciando extração do CRM")

    while True:

        if pagina in paginas_visitadas:
            raise RuntimeError(
                f"Paginação circular detectada: {pagina}"
            )

        paginas_visitadas.add(pagina)

        dados = buscar_pagina(pagina)
        lote = dados["data"]

        if not lote and dados.get("has_more"):
            raise RuntimeError(
                f"Página {pagina} vazia com has_more=True"
            )

        registros.extend(lote)

        logger.info(
            "Página %s | Recebidos: %s | Acumulado: %s",
            pagina,
            len(lote),
            len(registros)
        )

        if not dados["has_more"]:
            break

        proxima = dados.get("next_page")

        if not isinstance(proxima, int) or proxima <= pagina:
            raise RuntimeError(
                f"Próxima página inválida: {proxima}"
            )

        pagina = proxima

        # Respeitar limite da API
        time.sleep(0.25)

    total_esperado = dados.get("total")

    if total_esperado is not None:
        if len(registros) != total_esperado:
            raise RuntimeError(
                f"Extração incompleta: recebidos "
                f"{len(registros)} de {total_esperado}"
            )

    logger.info(
        "Extração finalizada | Total: %s | Páginas: %s",
        len(registros),
        len(paginas_visitadas)
    )

    return registros


# ==========================================
# PERSISTÊNCIA NO DUCKDB
# ==========================================

def gravar_duckdb(registros):

    logger.info("Iniciando gravação no DuckDB")

    linhas = []

    for registro in registros:

        json_original = json.dumps(
            registro,
            sort_keys=True,
            ensure_ascii=False
        )

        identificador = hashlib.sha256(
            json_original.encode("utf-8")
        ).hexdigest()

        linhas.append((
            identificador,
            registro["id"],
            registro["atualizado_em"],
            json_original
        ))

    hashes = [linha[0] for linha in linhas]

    total_unicos = len(set(hashes))
    duplicados = len(hashes) - total_unicos

    logger.info(
        "Qualidade | Recebidos: %s | Únicos: %s | "
        "Duplicados: %s",
        len(linhas),
        total_unicos,
        duplicados
    )

    conexao = duckdb.connect(str(BANCO))

    try:
        conexao.execute(
            "CREATE SCHEMA IF NOT EXISTS raw"
        )

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS raw.crm_deals (
                event_hash VARCHAR PRIMARY KEY,
                deal_id VARCHAR NOT NULL,
                atualizado_em VARCHAR NOT NULL,
                payload_json VARCHAR NOT NULL,
                ingerido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conexao.execute("BEGIN TRANSACTION")

        try:
            total_antes = conexao.execute("""
                SELECT COUNT(*) FROM raw.crm_deals
            """).fetchone()[0]

            conexao.executemany("""
                INSERT INTO raw.crm_deals (
                    event_hash,
                    deal_id,
                    atualizado_em,
                    payload_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT (event_hash) DO NOTHING
            """, linhas)

            total_depois = conexao.execute("""
                SELECT COUNT(*) FROM raw.crm_deals
            """).fetchone()[0]

            conexao.execute("COMMIT")

        except Exception:
            conexao.execute("ROLLBACK")
            raise

        logger.info(
            "Gravação concluída | Inseridos: %s | "
            "Total armazenado: %s",
            total_depois - total_antes,
            total_depois
        )

    finally:
        conexao.close()


# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================

def main():

    inicio = time.monotonic()

    try:
        if not TOKEN:
            raise RuntimeError(
                "Variável CRM_API_TOKEN não configurada"
            )

        registros = extrair_crm()
        gravar_duckdb(registros)

        duracao = time.monotonic() - inicio

        logger.info(
            "EXECUÇÃO CONCLUÍDA COM SUCESSO | "
            "Duração: %.2fs",
            duracao
        )

    except Exception:
        logger.exception(
            "EXECUÇÃO ENCERRADA COM ERRO"
        )
        raise


if __name__ == "__main__":
    main()
