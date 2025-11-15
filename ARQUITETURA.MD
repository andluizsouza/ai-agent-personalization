Este plano detalhado serve como um **Guia Técnico e de Arquitetura**, descrevendo a construção da solução "Assistente de Reabastecimento Inteligente" em etapas modulares.

## 📄 Guia Técnico de Construção da Solução (Plan-and-Execute)

A solução será construída em 4 fases, focando na **simplicidade** e **clareza** das decisões, mas garantindo a **robustez** e a **escalabilidade** (características exigidas para impressionar o gestor da BEES).

---

## 🛠️ Fase 1: Infraestrutura de Dados (As Fundações)

Esta fase configura todos os recursos de dados que os agentes consumirão.

### 1.1. Base de Dados Proprietária (Tool 1 - `Client_Profile_Knowledge`)

* **Ação:** Conectar ao banco de dados **SQLite** existente `customers.db` (com a tabela `client_profiles`).
* **Por que:** Simula a base de clientes proprietária da BEES. O uso de SQL é essencial para o padrão **Text-to-SQL**.
* **Decisão Técnica:** A chave para a integração no LangChain é a classe **`SQLDatabase`** (do SQLAlchemy), que estabelece a conexão usando `sqlite:///customers.db` e expõe o *schema* da tabela ao LLM.

### 1.2. RAG Index (Web Knowledge Cache - TTL)

* **Ação:** Inicializar o índice FAISS (`Web_Knowledge_Cache`) usando **Google Embeddings (`models/embedding-001`)**.
* **Por que:** Implementação da arquitetura de **Cache TTL (Time-to-Live)** para otimizar custos de busca web.
* **Decisão Técnica:** Os *chunks* armazenados (resumos de sites) devem ter **metadados estruturados**:
    ```json
    {
      "brewery_name": "Nome da Cervejaria",
      "url": "https://example.com",
      "summary": "Resumo conciso do site...",
      "creation_date": "2025-11-15",
      "brewery_type": "micro"
    }
    ```
* **Biblioteca:** Usar **FAISS** como banco vetorial local e **LangChain** para integração com embeddings do Google.

---

## ⚙️ Fase 2: Desenvolvimento Modular das Ferramentas (Tools)

Cada Tool é construída e testada isoladamente para garantir a robustez (padrão **Separation of Concerns**).

### 2.1. Tool 1: `get_client_profile`

* **Objetivo:** Receber `client_id` (ou dados de busca), executar a *query* no `customers.db` e retornar o perfil do cliente como um JSON estruturado.
* **Decisão Técnica:** Utilizar **Gemini 1.5 Flash** via LangChain com **Function Calling** para Text-to-SQL:
    1.  O **schema completo** da tabela `client_profiles` é injetado diretamente no **System Prompt** do SQL Runner (sem necessidade de RAG Index adicional).
    2.  O LLM (Gemini) gera a *query* SQL usando o schema fornecido.
    3.  O executor SQL executa a *query* na base `customers.db`.
    4.  A função deve incluir a lógica de *fallback* (procurar por `postal_code` e/ou `client_name` se o `client_id` for ausente).
    5.  Implementar um **Output Parser** para garantir que o resultado seja sempre um JSON estruturado:
        ```json
        {
          "client_id": "C001",
          "client_name": "Nome",
          "client_location_city_state": "San Diego, CA",
          "postal_code": "92101",
          "top3_brewery_types": ["micro", "brewpub", "regional"],
          "top_5_beers_recently": ["Beer 1", "Beer 2", ...],
          "brewery_history": ["Brewery A", "Brewery B", ...]
        }
        ```
    6.  **Formato de resposta interna:** Retornar JSON com `{"sql_query": "...", "search_method": "client_id|postal_code|client_name|not_found", "result": {...}}`

### 2.2. Tool 2: `search_breweries_by_location_and_type`

* **Objetivo:** Receber `city` e `brewery_type` (do Tool 1) e consultar a **API OpenBreweryDB**.
* **Decisão Técnica:** **Filtro de Histórico de Compras.** A função deve ter lógica interna para receber a lista `brewery_history` (do Tool 1) e **filtrar os resultados da API**, garantindo que apenas cervejarias *novas* (não presentes no histórico) sejam sugeridas. O resultado final deve conter o `name` e `website_url` da sugestão escolhida.
* **Tratamento de Erros Robusto:**
    - Se a API retornar erro: `{"error": "API_ERROR", "message": "descrição do erro"}`
    - Se não houver resultados na localização: `{"error": "NO_BREWERIES_IN_LOCATION"}`
    - Se todos os resultados já estiverem no histórico: `{"error": "NO_NEW_BREWERIES_FOUND"}`
    - Sucesso: `{"suggested_name": "Nome", "website_url": "https://...", "brewery_type": "micro"}`

### 2.3. Tool 3: `get_website_summary`

* **Objetivo:** Receber `url` e retornar o resumo do site, priorizando o cache (RAG Index FAISS).
* **Decisão Técnica:** Implementação da lógica de **Cache TTL e Fallback**:
    1.  Tentar busca semântica no **RAG Index (FAISS)** pelo nome/URL da cervejaria usando **Google Embeddings (`models/embedding-001`)**.
    2.  Se encontrado (Cache Hit): Checar o metadado `creation_date`. Se for mais antigo que 30 dias, marcar como **inválido** (Cache Stale).
    3.  Se Cache Miss ou Inválido: Disparar o **Google Search API** (via LangChain) para a URL.
    4.  Usar **BeautifulSoup** ou similar para extrair o conteúdo HTML limpo.
    5.  Usar **Gemini 1.5 Flash** para gerar um resumo conciso (máximo 3 frases).
    6.  Se for uma busca nova/atualização: Criar um novo *chunk* com metadados completos (brewery_name, url, summary, creation_date, brewery_type) e indexar no **RAG Index FAISS**, garantindo que o cache seja "aquecido" para o próximo cliente.
    7.  Salvar o índice FAISS atualizado no disco.

---

## 🧠 Fase 3: Orquestração (O Cérebro do Agente)

Esta fase une as ferramentas no Agente LangChain.

### 3.1. Definindo o LLM e o Agente

* **Ação:** Instanciar o **Gemini 1.5 Flash** via LangChain (`ChatGoogleGenerativeAI`) e o **Agente Executor** (`AgentExecutor`).
* **Decisão Técnica:** 
    - Usar **Function Calling/Tools** nativos do Gemini para garantir que o LLM chame as funções com *inputs* no formato correto.
    - Configurar o modelo com `temperature=0` para respostas determinísticas.
    - Usar a **API Key do Google AI** (não Vertex AI) para conexão direta.

### 3.2. Engenharia de Prompt (System Prompt)

* **Ação:** Aplicar o **System Prompt** rigoroso que definimos, garantindo o papel, o objetivo e o **Plano de Execução Obrigatório** de 5 passos.
* **Decisão Técnica:** O prompt é o principal guia do agente, forçando o fluxo: **Contexto (Tool 1) → Busca (Tool 2) → Otimização de Custo (Pergunta Condicional) → Detalhe (Tool 3)**.

### 3.3. Lógica Condicional (Passo 3 & 4)

* **Ação:** O código Python principal deve gerenciar o fluxo de conversação (chat loop).
* **Decisão Técnica:** Após o **Passo 3** (resposta inicial), o *loop* deve pausar, enviar a pergunta de otimização de custo ao usuário usando o formato exato: 
    > "Gostaria de ver um resumo detalhado sobre {brewery_name}? (Responda 'sim' ou 'não')"
* **Timeout:** Se não houver resposta em 30 segundos, assumir "não" e prosseguir diretamente para o Passo 5.
* **Controle:** Só chamar a **Tool 3** (`get_website_summary`) se a resposta for "Sim", "sim", "yes" ou variações. Isso é feito fora da lógica interna do LLM (no código do *Agent Handler*), garantindo controle de custos e latência.

---

## � Fase 4: Interface de Interação (Chat Conversacional)

Esta fase implementa a interface de usuário para testar e validar o agente em modo conversacional.

### 4.1. Script Main.py (CLI Interativo)

* **Objetivo:** Criar um script Python executável que permita interação via terminal em modo chat.
* **Funcionalidades:**
    - **Modo Interativo:** Loop conversacional que mantém o contexto da sessão
    - **Entrada de Client ID:** Permitir que o usuário informe o `client_id` no início ou deixe o agente identificá-lo
    - **Histórico de Conversa:** Manter mensagens anteriores visíveis para contexto
    - **Comandos Especiais:**
        * `/exit` ou `/quit` - Sair do chat
        * `/clear` - Limpar histórico da conversa
        * `/log` - Mostrar Chain-of-Thought da última execução
        * `/metrics` - Mostrar métricas de performance da sessão
    - **Feedback Visual:** Indicadores de status (🤔 Pensando..., ✅ Pronto, ⚠️ Erro)
    - **Tratamento de Timeout:** Interface clara para a pergunta condicional do Passo 3

* **Decisão Técnica:**
    - Usar biblioteca `rich` para interface colorida e formatada no terminal
    - Implementar classe `ChatSession` para gerenciar estado da conversa
    - Integrar com o `AgentExecutor` do LangChain mantendo contexto entre mensagens

* **Exemplo de Execução:**
```bash
# Modo interativo (usuário informa client_id durante conversa)
python main.py

# Modo direto com client_id
python main.py --client_id C001

# Modo debug (mostra logs detalhados)
python main.py --debug
```

### 4.2. Tratamento de Fluxo Conversacional

* **Ação:** Implementar lógica para gerenciar o fluxo dos 5 passos no contexto de chat:
    1. **Inicialização:** Apresentação do agente e solicitação do client_id (se não fornecido)
    2. **Contexto Automático:** Assim que o client_id é identificado, executar Tool 1 automaticamente
    3. **Sugestão Proativa:** Executar Tool 2 e apresentar sugestão
    4. **Pergunta Condicional:** Pausar e aguardar resposta do usuário com timeout visual
    5. **Continuação Natural:** Permitir que o usuário faça perguntas adicionais após conclusão

* **Decisão Técnica:** 
    - Implementar máquina de estados para controlar em qual passo o agente está
    - Usar `asyncio` para gerenciar timeout da pergunta condicional sem bloquear UI
    - Armazenar contexto da conversa em memória durante a sessão

---

## 🚀 Fase 5: API REST (FastAPI)

Esta fase disponibiliza o agente como serviço web para integração com outros sistemas.

### 5.1. API Endpoints

* **Objetivo:** Criar API REST completa para consumo do agente por aplicações externas.

#### Endpoint 1: POST /chat/message
* **Descrição:** Enviar mensagem para o agente e receber resposta
* **Request Body:**
```json
{
  "session_id": "uuid-opcional",
  "client_id": "C001",
  "message": "Sugira uma nova cervejaria local",
  "include_trace": false
}
```
* **Response:**
```json
{
  "session_id": "uuid",
  "response": "Texto da resposta do agente",
  "requires_input": false,
  "suggested_actions": ["confirm", "details"],
  "execution_time_ms": 3421,
  "trace": null
}
```

#### Endpoint 2: POST /chat/session
* **Descrição:** Criar nova sessão de chat
* **Response:**
```json
{
  "session_id": "uuid",
  "created_at": "2025-11-15T14:30:22Z",
  "status": "active"
}
```

#### Endpoint 3: GET /chat/session/{session_id}
* **Descrição:** Obter histórico e status de uma sessão
* **Response:**
```json
{
  "session_id": "uuid",
  "messages": [...],
  "client_id": "C001",
  "status": "active",
  "created_at": "...",
  "last_activity": "..."
}
```

#### Endpoint 4: DELETE /chat/session/{session_id}
* **Descrição:** Encerrar e limpar uma sessão

#### Endpoint 5: GET /health
* **Descrição:** Health check da API
* **Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "gemini_api": "connected",
    "faiss_index": "loaded"
  }
}
```

#### Endpoint 6: GET /metrics
* **Descrição:** Métricas agregadas do sistema
* **Response:**
```json
{
  "total_sessions": 42,
  "total_messages": 156,
  "avg_response_time_ms": 3200,
  "cache_hit_rate": 0.78,
  "uptime_seconds": 86400
}
```

### 5.2. Implementação Técnica

* **Framework:** FastAPI com Pydantic para validação
* **Autenticação:** API Key via header `X-API-Key` (opcional para POC, recomendado para produção)
* **CORS:** Configurado para permitir acesso de frontend
* **Rate Limiting:** Implementar limite de requisições por cliente
* **Session Management:** 
    - Usar Redis (opcional) ou memória para sessões ativas
    - TTL de 30 minutos para sessões inativas
* **Async/Await:** Todos os endpoints assíncronos para melhor performance
* **Error Handling:** Tratamento consistente de erros com códigos HTTP apropriados
* **Documentação:** OpenAPI/Swagger automático do FastAPI

### 5.3. Estrutura de Arquivos API

```
api/
├── __init__.py
├── main.py                 # App FastAPI principal
├── models/
│   ├── __init__.py
│   ├── request.py         # Pydantic models para requests
│   └── response.py        # Pydantic models para responses
├── routes/
│   ├── __init__.py
│   ├── chat.py            # Endpoints de chat
│   ├── health.py          # Health check
│   └── metrics.py         # Métricas
├── middleware/
│   ├── __init__.py
│   ├── auth.py            # API Key validation
│   └── rate_limit.py      # Rate limiting
└── session_manager.py     # Gerenciamento de sessões

```

### 5.4. Execução da API

```bash
# Desenvolvimento (com auto-reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker (opcional)
docker build -t bees-assistant-api .
docker run -p 8000:8000 bees-assistant-api
```

### 5.5. Exemplo de Uso da API

```python
import requests

# Criar sessão
session = requests.post("http://localhost:8000/chat/session")
session_id = session.json()["session_id"]

# Enviar mensagem
response = requests.post(
    "http://localhost:8000/chat/message",
    json={
        "session_id": session_id,
        "client_id": "C001",
        "message": "Sugira uma nova cervejaria local"
    },
    headers={"X-API-Key": "your-api-key"}
)

print(response.json()["response"])
```

---

## 📊 Fase 6: Observabilidade e Logging

Esta fase garante rastreabilidade completa da execução do agente para debugging e otimização.

### 4.1. Sistema de Logging

* **Ação:** Implementar logging estruturado para cada componente:
    - **Tool 1 (SQL Runner):** Logar `timestamp`, `client_id_input`, `sql_query_generated`, `search_method`, `execution_time_ms`, `result_status` (success/error).
    - **Tool 2 (New Opportunities):** Logar `timestamp`, `city`, `brewery_type`, `api_results_count`, `filtered_count`, `selected_brewery`, `execution_time_ms`.
    - **Tool 3 (Web Explorer):** Logar `timestamp`, `url`, `cache_status` (hit/miss/stale), `search_performed` (yes/no), `summary_length`, `execution_time_ms`.
    - **Planner (Orquestrador):** Gerar um **Chain-of-Thought trace completo** com a sequência de todas as tool calls, inputs e outputs.

* **Formato:** Salvar logs em arquivo JSON estruturado (`logs/execution_{timestamp}.json`) para análise posterior.

* **Decisão Técnica:** Usar o módulo `logging` do Python com formatação JSON e rotação de arquivos.

### 4.2. Métricas de Performance

* **Ação:** Calcular e reportar ao final de cada execução:
    - Tempo total de execução
    - Número de tool calls realizadas
    - Cache hit rate (Tool 3)
    - Custo estimado (baseado em tokens consumidos pelo Gemini)

---

## ✅ Fase 7: Teste e Validação

### 7.1. Testes Unitários e de Integração

* **Ação:** Testar cada Tool em isolamento:
    * **Tool 1:** Testar a recuperação do `client_id` (C001), `postal_code` (92101) e o *fallback* de busca. Validar formato JSON de saída.
    * **Tool 2:** Testar a busca por `San Diego, CA` e `micro`, garantindo que cervejarias listadas no `brewery_history` do cliente C001 **não** sejam sugeridas. Testar todos os cenários de erro (API_ERROR, NO_BREWERIES_IN_LOCATION, NO_NEW_BREWERIES_FOUND).
    * **Tool 3:** Testar o Cache Hit (data recente), Cache Stale (data > 30 dias) e Cache Miss para validar a lógica TTL completa. Verificar persistência do índice FAISS.

### 7.2. Teste do Script Main.py (CLI)

* **Ação:** Validar a interface conversacional:
    - Testar fluxo completo: inicialização → consulta → sugestão → resposta condicional → conclusão
    - Testar comandos especiais (`/exit`, `/clear`, `/log`, `/metrics`)
    - Testar timeout da pergunta condicional (30s)
    - Validar formatação visual com `rich`
    - Testar modo debug

### 7.3. Teste da API FastAPI

* **Ação:** Validar todos os endpoints:
    - Testar criação de sessão
    - Testar envio de mensagens com/sem session_id
    - Testar health check
    - Testar métricas agregadas
    - Validar tratamento de erros (client_id inválido, sessão inexistente, etc.)
    - Testar rate limiting
    - Validar documentação Swagger em `/docs`

### 7.4. Teste de Ponta a Ponta (E2E)

* **Ação:** Executar a consulta alvo:
    > "Estou fazendo meu pedido semanal. Baseado no meu perfil de cliente (RAG), me lembre quais são as 3 cervejas que mais peço. Além disso, sugira uma nova cervejaria local de San Diego (API) que seja do mesmo tipo de estabelecimento que a maioria das minhas fornecedoras ('micro')."
* **Entrega Final (CLI):** Demonstração em vídeo/screenshot mostrando:
    1. Execução do `main.py` em modo interativo
    2. Conversa completa com o agente
    3. Visualização do log com comando `/log`
    4. Métricas com comando `/metrics`

* **Entrega Final (API):** 
    1. API rodando em `http://localhost:8000`
    2. Documentação Swagger acessível em `http://localhost:8000/docs`
    3. Exemplos de requests/responses para cada endpoint
    4. Collection do Postman/Insomnia para testes

---

## 🔧 Stack Tecnológico Final

| Componente | Tecnologia | Justificativa |
|:-----------|:-----------|:--------------|
| **LLM Principal** | Gemini 1.5 Flash via LangChain | Baixa latência, excelente Function Calling, custo otimizado |
| **Embeddings** | Google `models/embedding-001` | Integração nativa com Google AI, alta qualidade |
| **Banco Vetorial** | FAISS (local) | Gratuito, rápido, ideal para datasets pequenos/médios |
| **Banco de Dados** | SQLite (`customers.db`) | Já existente, zero configuração, perfeito para POC |
| **Web Search** | Google Search API via LangChain | Alta qualidade de resultados, integração nativa |
| **Framework** | LangChain | Abstrações prontas para Agents, Tools, Chains |
| **Logging** | Python `logging` + JSON | Estruturado, rastreável, analisável |
| **CLI Interface** | Rich + asyncio | Interface moderna, timeout visual, UX profissional |
| **API REST** | FastAPI + Pydantic | Performance assíncrona, documentação automática, validação robusta |
| **Session Management** | In-memory (ou Redis) | Stateful, escalável, TTL automático |

---

Este plano garante que todos os critérios técnicos (LangChain, FAISS, API, Múltiplas Ferramentas, Simplicidade, Clareza) sejam cumpridos, enquanto resolve problemas de engenharia de produção (Escalabilidade, Custo/Latência, Observabilidade e **Integração com Sistemas Externos**).