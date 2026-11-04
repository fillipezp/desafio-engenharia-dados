from unittest.mock import patch, Mock

import pytest
import requests

from ingestao.extrair_crm import buscar_pagina
from ingestao.extrair_crm import extrair_crm


def test_buscar_pagina_sucesso():

    # Criar uma resposta HTTP simulada
    resposta = Mock()
    resposta.status_code = 200

    resposta.json.return_value = {
        "data": [
            {
                "id": "D-001",
                "etapa": "lead"
            }
        ],
        "page": 1,
        "has_more": False,
        "next_page": None,
        "total": 1
    }

    # Substituir temporariamente o requests.get
    with patch(
        "ingestao.extrair_crm.requests.get",
        return_value=resposta
    ) as requisicao_simulada:

        resultado = buscar_pagina(1)

    # Verificar o resultado
    assert len(resultado["data"]) == 1
    assert resultado["data"][0]["id"] == "D-001"
    assert resultado["has_more"] is False

    # Garantir que a API foi chamada uma única vez
    assert requisicao_simulada.call_count == 1


#############################################
## Testar a recuperação com o código 500   ##
#############################################
def test_erro_500_com_recuperacao():

    # Primeira resposta: API apresenta erro
    resposta_erro = Mock()
    resposta_erro.status_code = 500
    resposta_erro.headers = {}

    # Segunda resposta: API volta a funcionar
    resposta_sucesso = Mock()
    resposta_sucesso.status_code = 200
    resposta_sucesso.json.return_value = {
        "data": [{"id": "D-001"}],
        "page": 1,
        "has_more": False,
        "next_page": None,
        "total": 1
    }

    # Cada chamada retorna uma resposta diferente
    with patch(
        "ingestao.extrair_crm.requests.get",
        side_effect=[resposta_erro, resposta_sucesso]
    ) as requisicao:

        # Simular a espera, sem aguardar de verdade
        with patch("ingestao.extrair_crm.time.sleep"):

            resultado = buscar_pagina(1)

    # Verificar se recuperou o registro
    assert resultado["data"][0]["id"] == "D-001"

    # Verificar se fez duas tentativas
    assert requisicao.call_count == 2


#########################################
## Testar o 401 de não autorizado      ##
#########################################
def test_erro_401():
    resposta_erro_401 = Mock()
    resposta_erro_401.status_code = 401

    resposta_erro_401.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("401 Unauthorized")
    )

    with patch(
        "ingestao.extrair_crm.requests.get",
        return_value=resposta_erro_401
    ) as requisicao:
        with pytest.raises(requests.exceptions.HTTPError):
            buscar_pagina(1)

    assert requisicao.call_count == 1        



#############################################
## Testar a paginação completa do extrator ##
#############################################
def test_paginacao_completa():

    # Respostas simuladas das três páginas
    paginas = [
        {
            "data": [
                {"id": "D-001"},
                {"id": "D-002"}
            ],
            "page": 1,
            "has_more": True,
            "next_page": 2,
            "total": 5
        },
        {
            "data": [
                {"id": "D-003"},
                {"id": "D-004"}
            ],
            "page": 2,
            "has_more": True,
            "next_page": 3,
            "total": 5
        },
        {
            "data": [
                {"id": "D-005"}
            ],
            "page": 3,
            "has_more": False,
            "next_page": None,
            "total": 5
        }
    ]

    with patch(
        "ingestao.extrair_crm.buscar_pagina",
        side_effect=paginas
    ) as buscar:

        with patch("ingestao.extrair_crm.time.sleep"):

            registros = extrair_crm()

    # Verificar quantidade total
    assert len(registros) == 5

    # Verificar ordem e IDs extraídos
    ids = [registro["id"] for registro in registros]

    assert ids == [
        "D-001",
        "D-002",
        "D-003",
        "D-004",
        "D-005"
    ]

    # Verificar se todas as páginas foram consultadas
    assert buscar.call_count == 3

    # Verificar a sequência das páginas
    assert [
        chamada.args[0]
        for chamada in buscar.call_args_list
    ] == [1, 2, 3]



def test_paginacao_invalida():

    pagina_invalida = {
        "data": [{"id": "D-001"}],
        "page": 1,
        "has_more": True,
        "next_page": 1,
        "total": 2
    }

    with patch(
        "ingestao.extrair_crm.buscar_pagina",
        return_value=pagina_invalida
    ) as buscar:

        with pytest.raises(
            RuntimeError,
            match="Próxima página inválida"
        ):
            extrair_crm()

    assert buscar.call_count == 1
