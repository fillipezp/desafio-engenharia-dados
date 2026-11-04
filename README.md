# Desafio: funil de vendas

Kit do desafio técnico para a vaga de Engenheiro(a) de Dados da +A Educação.
O enunciado completo está no documento que você recebeu junto com este kit.

## Estrutura

```
api/            API simulada do CRM (não leia _store.json.gz diretamente)
data/erp/       extração de matrículas do ERP (CSV)
ingestao/       seu código de extração
tests/          seus testes
models/         seus modelos dbt (sources.yml já configurado)
ENTREGA.md      modelo do README da sua entrega
```

## Como rodar

Requer Python 3.10 ou superior. Tudo roda localmente: não precisa de conta em nuvem nem de Docker.

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# terminal 1: sobe a API do CRM
python api/crm_api.py

# terminal 2
export CRM_API_TOKEN=desafio-maisa-2026   # no Windows: set CRM_API_TOKEN=desafio-maisa-2026
dbt debug --profiles-dir .
```

O banco é o arquivo `funil.duckdb` na raiz, compartilhado pelo seu extrator e pelo dbt.
O source `crm.deals` espera a tabela `raw.crm_deals`; se usar outro nome, ajuste `models/sources.yml`.

## API do CRM

`GET http://localhost:8000/deals`

| Parâmetro | Obrigatório | Descrição |
| --- | --- | --- |
| `page` | não | Página, a partir de 1. Padrão 1 |
| `page_size` | não | Registros por página. Padrão 50, máximo 100 |
| `updated_since` | não | Data e hora ISO 8601. Devolve registros com `atualizado_em` maior ou igual a ela |

Autenticação: header `Authorization: Bearer <token>`.

Resposta:

```json
{
  "data": [ { "id": "D-00001", "etapa": "lead", "atualizado_em": "2026-10-01T14:22:00Z", "...": "..." } ],
  "page": 1, "page_size": 50, "total": 9436,
  "has_more": true, "next_page": 2
}
```

Cada registro é o estado de um deal num momento: o mesmo deal aparece mais de uma vez,
uma por atualização. Os registros vêm ordenados por `atualizado_em`.

Como qualquer API de terceiro, esta tem limite de requisições e às vezes falha.
Consulte os códigos HTTP e os headers das respostas.

`GET /health` responde sem autenticação, útil para conferir se a API está no ar.

### Simulando a passagem do tempo

```bash
python api/crm_api.py --ate 2026-10-04   # a API como estava no fim de 04/10
```

Útil para testar carga incremental: extraia com `--ate 2026-10-04`, reinicie a API sem o parâmetro e extraia de novo.
