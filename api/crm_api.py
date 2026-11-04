"""API simulada do CRM para o desafio técnico.

Uso:
    python api/crm_api.py                  # estado da API em 07/10/2026
    python api/crm_api.py --ate 2026-10-04 # simula a API como estava no fim de 04/10

Só usa a biblioteca padrão do Python. Não leia _store.json.gz diretamente:
a extração faz parte do desafio e precisa passar pela API.
"""
import argparse
import gzip
import json
import random
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOKEN = "desafio-maisa-2026"
LIMITE_POR_SEGUNDO = 5
TAXA_ERRO_500 = 0.08
PAGE_SIZE_PADRAO = 50
PAGE_SIZE_MAX = 100
INICIO_SCHEMA_V2 = datetime(2026, 10, 6, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
BRT = timezone(timedelta(hours=-3))


def parse_ts(valor):
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def carregar(ate):
    caminho = Path(__file__).with_name("_store.json.gz")
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        regs = json.load(f)
    limite = datetime(ate.year, ate.month, ate.day, tzinfo=BRT) + timedelta(days=1)
    regs = [r for r in regs if parse_ts(r["atualizado_em"]) < limite]
    # ordem estável por data de atualização, como a API real
    regs.sort(key=lambda r: (parse_ts(r["atualizado_em"]), r["id"]))
    return regs


def aplicar_schema(reg):
    """A partir de 06/10 o CRM passou a devolver o valor como objeto."""
    if parse_ts(reg["atualizado_em"]) < INICIO_SCHEMA_V2:
        return reg
    novo = {k: v for k, v in reg.items() if k not in ("valor", "moeda")}
    novo["valor"] = None if reg["valor"] is None else {"amount": reg["valor"], "currency": reg.get("moeda", "BRL")}
    return novo


class Estado:
    def __init__(self, regs):
        self.regs = regs
        self.chamadas = deque()
        self.lock = threading.Lock()
        self.rng = random.Random()

    def estourou_limite(self):
        agora = time.monotonic()
        with self.lock:
            while self.chamadas and agora - self.chamadas[0] > 1:
                self.chamadas.popleft()
            if len(self.chamadas) >= LIMITE_POR_SEGUNDO:
                return True
            self.chamadas.append(agora)
            return False


class Handler(BaseHTTPRequestHandler):
    estado = None

    def _json(self, status, corpo, headers=None):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self._json(200, {"status": "ok"})
        if url.path != "/deals":
            return self._json(404, {"erro": "rota não encontrada"})
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self._json(401, {"erro": "token ausente ou inválido"})
        if self.estado.estourou_limite():
            return self._json(429, {"erro": "limite de requisições excedido"}, {"Retry-After": "1"})
        if self.estado.rng.random() < TAXA_ERRO_500:
            return self._json(500, {"erro": "erro interno, tente novamente"})

        q = parse_qs(url.query)
        try:
            pagina = int(q.get("page", ["1"])[0])
            tamanho = min(int(q.get("page_size", [str(PAGE_SIZE_PADRAO)])[0]), PAGE_SIZE_MAX)
            desde = parse_ts(q["updated_since"][0]) if "updated_since" in q else None
        except (ValueError, KeyError):
            return self._json(400, {"erro": "parâmetro inválido"})
        if pagina < 1 or tamanho < 1:
            return self._json(400, {"erro": "page e page_size devem ser positivos"})

        regs = self.estado.regs
        if desde is not None:
            regs = [r for r in regs if parse_ts(r["atualizado_em"]) >= desde]
        inicio = (pagina - 1) * tamanho
        fatia = [aplicar_schema(r) for r in regs[inicio:inicio + tamanho]]
        tem_mais = inicio + tamanho < len(regs)
        return self._json(200, {
            "data": fatia,
            "page": pagina,
            "page_size": tamanho,
            "total": len(regs),
            "has_more": tem_mais,
            "next_page": pagina + 1 if tem_mais else None,
        })

    def log_message(self, fmt, *args):
        print(f"[crm-api] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


def main():
    p = argparse.ArgumentParser(description="API simulada do CRM")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--ate", default="2026-10-07", help="data (AAAA-MM-DD) até a qual a API tem dados")
    a = p.parse_args()
    ate = datetime.strptime(a.ate, "%Y-%m-%d").date()
    Handler.estado = Estado(carregar(ate))
    print(f"API do CRM em http://localhost:{a.porta}  |  dados até {ate}  |  {len(Handler.estado.regs)} registros")
    ThreadingHTTPServer(("127.0.0.1", a.porta), Handler).serve_forever()


if __name__ == "__main__":
    main()
