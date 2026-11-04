# Desafio Técnico — Engenharia de Dados

## 1. Como rodar

O projeto utiliza Python, DuckDB e dbt, com execução totalmente local, sem necessidade de Docker ou serviços em nuvem.

**Pré-requisitos:** Python 3.10 ou superior.

Na raiz do projeto, utilizando PowerShell no Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

**Terminal 1 — Iniciar a API:**

```powershell
py api/crm_api.py
```

A API estará disponível em `http://localhost:8000`. É possível verificar seu funcionamento acessando `/health`.

**Terminal 2 — Executar a ingestão e as transformações:**

```powershell
.\.venv\Scripts\Activate.ps1
$env:CRM_API_TOKEN = "desafio-maisa-2026"

py ingestao/extrair_crm.py
dbt build --profiles-dir .
```

O extrator cria o arquivo `funil.duckdb` e a tabela `raw.crm_deals` automaticamente. Em seguida, o dbt constrói os modelos e executa os testes de qualidade.

**Testes automatizados do extrator:**

```powershell
py -m pytest tests/test_extrator.py -v
```

## 2. Ingestão

O extrator foi desenvolvido em Python, utilizando `requests` para consumo da API REST e `duckdb` para persistência.

**Paginação:** percorre todas as páginas utilizando `has_more` e `next_page`, com até 100 registros por requisição. Também valida a contagem total e identifica paginações inconsistentes.

**Tratamento de erros:** utiliza até cinco tentativas para falhas temporárias, como HTTP 429, HTTP 5xx e erros de conexão, com intervalos de espera. Erros definitivos, como HTTP 401, interrompem o processo.

**Idempotência:** utiliza SHA-256 calculado a partir do JSON normalizado. O hash funciona como chave primária, e a instrução `ON CONFLICT DO NOTHING` evita a reinserção de registros idênticos.

**Histórico:** diferentes atualizações de um mesmo `deal_id` são preservadas. O extrator não substitui versões anteriores pela última atualização.

**Consistência:** a inserção dos registros utiliza transação, com `COMMIT` em caso de sucesso e `ROLLBACK` em caso de falha.

**Logs:** utiliza a biblioteca `logging`, registrando páginas processadas, retentativas, erros, duplicatas, quantidade de inserções e duração da execução no arquivo `logs/ingestao_crm.log`.

### Resultado da ingestão

| Indicador | Quantidade |
|---|---:|
| Registros retornados pela API | 9.436 |
| Ocorrências duplicadas por conteúdo | 90 |
| Registros distintos armazenados | 9.346 |
| Deals distintos | 4.167 |
| Páginas processadas | 95 |

A segunda execução da ingestão inseriu zero registros, confirmando a idempotência para o conjunto de dados utilizado.

A carga incremental não foi implementada.

## 3. Modelagem

A solução foi organizada seguindo os conceitos da arquitetura Medallion.

### Bronze

- `raw.crm_deals`: armazena os registros brutos do CRM, preservando o JSON original de cada versão, identificador, hash e metadados de ingestão.

### Silver

- `stg_crm_deals`: extrai os campos do JSON, converte datas e valores e padroniza as etapas comerciais.
- `stg_erp_matriculas`: trata o CSV do ERP, convertendo datas brasileiras, valores monetários e campos textuais.
- `int_deals_atual`: identifica a versão mais recente de cada oportunidade utilizando `ROW_NUMBER()` por `deal_id`.

### Gold

- `mart_funil`: apresenta a quantidade de oportunidades e os valores por etapa atual do funil comercial.
- `mart_receita_diaria`: apresenta matrículas pagas e receita confirmada agrupadas pela data da matrícula.

Os modelos Silver foram materializados como views, enquanto os marts da Gold foram criados como tabelas.

### Resultados analíticos

| Indicador | Resultado |
|---|---:|
| Oportunidades comerciais | 4.167 |
| Valor total do funil | R$ 3.517.414,50 |
| Oportunidades ganhas | 417 |
| Valor das oportunidades ganhas | R$ 877.500,50 |
| Matrículas pagas | 275 |
| Receita confirmada | R$ 692.611,00 |

O valor total do funil não representa receita recebida, pois inclui oportunidades em diferentes etapas.

## 4. Problemas encontrados e decisões adotadas

**Duplicações na API:** foram identificadas 90 ocorrências repetidas por conteúdo. Foi adotada deduplicação técnica por SHA-256, mantendo diferentes versões do mesmo deal.

**Falhas HTTP:** a API apresentou erros temporários HTTP 500 durante a extração. Foram implementadas retentativas com espera progressiva. Também foi validada a interrupção em caso de HTTP 401.

**Inconsistências nas etapas:** foram encontradas variações como `ganho`, `Ganho`, `GANHO `, `won`, `negociação` e `Negociacao`. Os valores foram padronizados para as seis etapas oficiais.

**Mudança na estrutura do JSON:** o campo `valor` aparece como número ou objeto contendo `amount` e `currency`. O staging foi desenvolvido para interpretar ambos os formatos.

**Datas em formatos diferentes:** o CRM utiliza timestamps com fusos horários, enquanto o ERP apresenta datas no formato brasileiro. As conversões foram tratadas na Silver.

**Valores nulos:** foram identificados registros sem valor comercial informado, preservados sem substituições artificiais no staging.

**Matrículas sem vínculo:** cinco matrículas pagas não possuem `deal_id`. Elas foram preservadas no cálculo da receita, pois a ausência do vínculo não invalida o pagamento registrado no ERP.

## 5. Premissas e definição de venda

Foram adotadas duas definições distintas:

- **Venda comercial:** oportunidade cuja etapa atual no CRM é `ganho`.
- **Receita confirmada:** matrícula com `status_pagamento = 'pago'` no ERP.

Para o indicador financeiro, foi adotado o ERP como fonte de referência, pois registra o status do pagamento.

A data da matrícula foi utilizada no agrupamento diário por não haver uma data efetiva de pagamento no arquivo disponibilizado. Portanto, o mart não representa necessariamente a data em que o dinheiro foi recebido.

Para determinar o estado atual de um deal, foi utilizada a atualização mais recente. Em caso de empate de timestamp, o hash é utilizado como critério determinístico de desempate, sem representar necessariamente a ordem real dos eventos.

Registros com JSON integralmente idêntico são considerados a mesma versão para deduplicação técnica.

## 6. Extensões implementadas

### Testes automatizados do extrator

Foram desenvolvidos cinco testes com `pytest` e `unittest.mock`, sem dependência da API em execução:

1. Resposta HTTP 200.
2. Recuperação após erro temporário HTTP 500.
3. Interrupção por erro definitivo HTTP 401.
4. Paginação completa.
5. Identificação de paginação inválida.

**Resultado:** cinco testes aprovados.

### Reconciliação CRM × ERP

Foi desenvolvida uma consulta de auditoria para comparar oportunidades ganhas no CRM com matrículas pagas no ERP.

Os resultados encontrados foram:

| Indicador | Resultado |
|---|---:|
| Deals ganhos | 417 |
| Deals ganhos com pagamento vinculado | 270 |
| Deals ganhos sem pagamento vinculado | 147 |
| Pagamentos vinculados aos deals ganhos | R$ 680.161,00 |
| Matrículas pagas sem vínculo com CRM | 5 |
| Valor dessas matrículas sem vínculo | R$ 12.450,00 |

Os valores pagos associados aos deals ganhos, somados aos pagamentos sem `deal_id`, correspondem à receita confirmada de R$ 692.611,00.

A análise demonstra a importância de separar o fechamento comercial da confirmação financeira.

### Proposta de orquestração

Em produção, utilizaria o Prefect para orquestrar o pipeline, definindo um flow com etapas de ingestão do CRM, execução do `dbt build` e validação dos resultados. Configuraria agendamento periódico, monitoramento dos estados das execuções, retentativas para falhas transitórias e alertas em caso de erro definitivo. Os logs e indicadores de qualidade seriam utilizados para diagnóstico, e a execução só seria considerada concluída após o sucesso das etapas e validações.

A orquestração foi documentada como proposta e não implementada no ambiente local.

### Extensões não implementadas

Não foram implementadas a carga incremental e a análise histórica de conversão por etapa. A prioridade foi concluir e validar os requisitos obrigatórios e as extensões selecionadas.

## 7. Testes e validação

Foram implementados 16 testes de qualidade no dbt, incluindo `not_null`, `unique` e `accepted_values` nos campos críticos.

**Resultado da execução:**

- 5 modelos construídos.
- 16 testes dbt aprovados.
- 5 testes Python aprovados.
- Nenhum erro nos testes executados.

Também foi realizada uma execução completa em um ambiente limpo, recriando o banco DuckDB e executando novamente a ingestão e o `dbt build --profiles-dir .`, ambos com sucesso.

## 8. Uso de IA

Utilizei o ChatGPT como ferramenta de apoio ao desenvolvimento e aprendizado, principalmente na estruturação do código Python, elaboração de testes automatizados, construção dos modelos SQL/dbt e revisão da documentação.

As sugestões foram analisadas e testadas localmente. Durante o desenvolvimento, foram necessários ajustes em consultas SQL, referências de colunas entre modelos e configurações do ambiente Python após a alteração do diretório do projeto.

Também foram executadas auditorias para verificar os resultados e confirmar as regras de negócio, em vez de depender somente do sucesso de execução dos códigos.

## 9. O que faria com mais tempo

- Implementaria carga incremental com controle de watermark e tratamento de atualizações tardias.
- Ampliaria os testes automatizados para situações adicionais de falha e persistência.
- Otimizaria a inserção dos registros no DuckDB utilizando operações em lote.
- Implementaria a orquestração e o monitoramento com Prefect.
- Desenvolveria indicadores de conversão histórica das oportunidades.
