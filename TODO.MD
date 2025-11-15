Essa é uma decisão excelente. Ao utilizar o **Gemini-Flash** e a **API de Embeddings da Google**, você mantém a qualidade e a velocidade necessárias para um Agente em produção, enquanto otimiza o uso de recursos gratuitos ou de baixo custo, conforme solicitado.

A arquitetura lógica que definimos (**Plan-and-Execute, Text-to-SQL, Cache TTL**) é robusta o suficiente para a transição. As informações adicionais necessárias para a construção (e que confirmam o seu pedido) são sobre a **conexão e as bibliotecas específicas** a serem usadas, mantendo o restante da infraestrutura (SQLite, FAISS/ChromaDB) local.

---

## 🛠️ Stack Tecnológico Final - Decisões Confirmadas

As principais decisões técnicas para a construção, focando na integração direta com as APIs do Google e ferramentas locais:

### 1. LLM e Orquestração (Agente Planejador e Executores)

| Componente | Decisão Técnica | Implementação |
| :--- | :--- | :--- |
| **Modelo Principal** | **Gemini 1.5 Flash** | Via LangChain: `ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)` |
| **Conexão** | **Google AI API Key** (não Vertex AI) | Configurar via variável de ambiente `GOOGLE_API_KEY` |
| **System Prompts** | Injeção direta no prompt | Schema SQL injetado no prompt do SQL Runner (sem RAG adicional) |
| **Function Calling** | Nativo do Gemini | LangChain `@tool` decorator para definir as 3 tools |
| **Framework** | **LangChain** | Usar `AgentExecutor` com Gemini como backend |

### 2. RAG e Embeddings (Cache Web - TTL)

| Componente | Decisão Técnica | Implementação |
| :--- | :--- | :--- |
| **Modelo de Embeddings** | **Google `models/embedding-001`** | Via LangChain: `GoogleGenerativeAIEmbeddings(model="models/embedding-001")` |
| **Base Vetorial** | **FAISS (local)** | `FAISS.from_documents()` + `FAISS.save_local()` / `FAISS.load_local()` |
| **Metadados dos Chunks** | JSON estruturado | `{"brewery_name": "...", "url": "...", "summary": "...", "creation_date": "YYYY-MM-DD", "brewery_type": "..."}` |
| **TTL (Time-to-Live)** | 30 dias | Cálculo: `(datetime.now() - datetime.fromisoformat(creation_date)).days > 30` |

**OBS:** Não haverá RAG Index 1 para Text-to-SQL. O schema será injetado diretamente no System Prompt do SQL Runner.

### 3. Banco de Dados SQL

| Componente | Decisão Técnica | Implementação |
| :--- | :--- | :--- |
| **Banco de Dados** | **SQLite** (`customers.db`) | Arquivo local já existente |
| **Conexão** | LangChain SQLDatabase | `SQLDatabase.from_uri("sqlite:///customers.db")` |
| **Tabela** | `client_profiles` | Schema completo injetado no prompt do SQL Runner |

### 4. APIs Externas

| Componente | Decisão Técnica | Implementação |
| :--- | :--- | :--- |
| **Busca de Cervejarias** | **OpenBreweryDB API** | Requisição direta via `requests`: `https://api.openbrewerydb.org/v1/breweries` |
| **Web Search (Fallback)** | **Google Search API** | Via LangChain Tool ou SDK do Google |
| **Web Scraping** | **BeautifulSoup4** | Extração de conteúdo HTML limpo antes de resumir com Gemini |

### 5. Logging e Observabilidade

| Componente | Decisão Técnica | Implementação |
| :--- | :--- | :--- |
| **Sistema de Log** | Python `logging` + JSON | Logs estruturados salvos em `logs/execution_{timestamp}.json` |
| **Métricas** | Rastreamento manual | Tempo de execução, tool calls, cache hit rate, tokens estimados |
| **Chain-of-Thought** | Trace completo | Sequência de tool calls + inputs/outputs + decisões condicionais |

---

## 🎯 Roadmap de Implementação

Com a infraestrutura lógica e as ferramentas definidas, a construção segue esta sequência:

### Fase 1: Setup Inicial
1. **Dependências:**
   ```bash
   pip install langchain langchain-google-genai faiss-cpu beautifulsoup4 requests sqlalchemy
   ```

2. **Variáveis de Ambiente:**
   ```bash
   export GOOGLE_API_KEY="sua-api-key-aqui"
   ```

3. **Estrutura de Diretórios:**
   ```
   BESS-TecnicalCase/
   ├── customers.db              # Banco SQLite (já existe)
   ├── tools/                    # Ferramentas (Tools)
   │   ├── __init__.py
   │   ├── sql_runner.py        # Tool 1
   │   ├── brewery_finder.py    # Tool 2
   │   └── web_explorer.py      # Tool 3
   ├── agents/                   # Agentes
   │   ├── __init__.py
   │   └── planner.py           # Agente Orquestrador
   ├── utils/                    # Utilitários
   │   ├── __init__.py
   │   ├── logger.py            # Sistema de logging
   │   ├── rag_manager.py       # Gerenciamento do FAISS
   │   └── chat_session.py      # Gerenciamento de sessão de chat
   ├── api/                      # API REST (FastAPI)
   │   ├── __init__.py
   │   ├── main.py              # App FastAPI principal
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── request.py       # Pydantic request models
   │   │   └── response.py      # Pydantic response models
   │   ├── routes/
   │   │   ├── __init__.py
   │   │   ├── chat.py          # Endpoints de chat
   │   │   ├── health.py        # Health check
   │   │   └── metrics.py       # Métricas
   │   ├── middleware/
   │   │   ├── __init__.py
   │   │   ├── auth.py          # API Key validation
   │   │   └── rate_limit.py    # Rate limiting
   │   └── session_manager.py   # Gerenciamento de sessões
   ├── prompts/                  # System Prompts (já existe)
   ├── data/                     # Dados persistentes
   │   └── faiss_index/         # Índice FAISS salvo
   ├── logs/                     # Logs de execução
   ├── tests/                    # Testes unitários e E2E
   │   ├── __init__.py
   │   ├── test_tools.py
   │   ├── test_agent.py
   │   └── test_api.py
   ├── main.py                   # CLI Conversacional
   ├── requirements.txt          # Dependências
   └── .env.example              # Exemplo de variáveis de ambiente
   ```

### Fase 2: Construção das Tools
1. **Tool 1 (SQL Runner):**
   - Conectar ao `customers.db` via `SQLDatabase`
   - Implementar geração de SQL via Gemini com schema injetado
   - Adicionar lógica de fallback (client_id → postal_code → client_name)
   - Retornar JSON estruturado com resultado

2. **Tool 2 (Brewery Finder):**
   - Chamar OpenBreweryDB API com filtros
   - Implementar filtro de histórico (case-insensitive)
   - Tratamento robusto de erros (API_ERROR, NO_BREWERIES, NO_NEW_BREWERIES)
   - Retornar JSON estruturado

3. **Tool 3 (Web Explorer):**
   - Inicializar/Carregar índice FAISS com Google Embeddings
   - Implementar lógica de Cache TTL (30 dias)
   - Fallback para Google Search + BeautifulSoup + Gemini
   - Persistir índice FAISS após atualização
   - Retornar JSON com source (cache/web_search)

### Fase 3: Agente Orquestrador
1. **Planner Agent:**
   - Inicializar Gemini 1.5 Flash via LangChain
   - Registrar as 3 Tools com `@tool` decorator
   - Implementar System Prompt completo (5 passos)
   - Adicionar lógica condicional (Passo 3/4) com timeout 30s
   - Gerenciar chat loop com estado

### Fase 4: Logging e Observabilidade
1. **Sistema de Logging:**
   - Configurar `logging` com formato JSON
   - Logar cada tool call (timestamp, args, result, execution_time)
   - Gerar Chain-of-Thought trace ao final
   - Calcular métricas (tempo total, cache hit rate, tokens)

### Fase 5: Interface CLI (main.py)
1. **Script Conversacional Interativo:**
   - Implementar classe `ChatSession` para gerenciar estado
   - Usar biblioteca `rich` para interface colorida e formatada
   - Implementar loop conversacional com contexto persistente
   - Adicionar comandos especiais:
     * `/exit` ou `/quit` - Sair
     * `/clear` - Limpar histórico
     * `/log` - Mostrar Chain-of-Thought
     * `/metrics` - Mostrar métricas da sessão
   - Implementar timeout visual (30s) para pergunta condicional
   - Adicionar indicadores de status (🤔 Pensando, ✅ Pronto, ⚠️ Erro)
   - Suporte para modo debug (`--debug`)

2. **Modos de Execução:**
   ```bash
   python main.py                    # Modo interativo
   python main.py --client_id C001   # Com client_id pré-definido
   python main.py --debug            # Modo debug
   ```

### Fase 6: API REST (FastAPI)
1. **Setup FastAPI:**
   - Criar estrutura de diretórios `api/`
   - Implementar Pydantic models (request/response)
   - Configurar CORS e middleware

2. **Implementar Endpoints:**
   - `POST /chat/message` - Enviar mensagem ao agente
   - `POST /chat/session` - Criar nova sessão
   - `GET /chat/session/{session_id}` - Obter histórico
   - `DELETE /chat/session/{session_id}` - Encerrar sessão
   - `GET /health` - Health check
   - `GET /metrics` - Métricas agregadas

3. **Session Management:**
   - Implementar gerenciador de sessões (in-memory ou Redis)
   - TTL de 30 minutos para sessões inativas
   - Cleanup automático de sessões expiradas

4. **Segurança e Performance:**
   - Implementar API Key authentication (header `X-API-Key`)
   - Rate limiting por cliente
   - Tratamento robusto de erros HTTP
   - Async/await em todos os endpoints

5. **Documentação:**
   - Documentação automática Swagger em `/docs`
   - Criar collection Postman/Insomnia
   - Exemplos de uso para cada endpoint

6. **Execução:**
   ```bash
   uvicorn api.main:app --reload          # Desenvolvimento
   uvicorn api.main:app --workers 4       # Produção
   ```

### Fase 7: Testes
1. **Testes Unitários:**
   - Testar Tool 1 com diferentes métodos de busca
   - Testar Tool 2 com cenários de erro
   - Testar Tool 3 com cache hit/miss/stale

2. **Teste CLI (main.py):**
   - Executar em modo interativo
   - Testar todos os comandos especiais
   - Validar timeout da pergunta condicional
   - Verificar formatação visual com rich
   - Testar modo debug

3. **Teste API (FastAPI):**
   - Testar criação e gerenciamento de sessões
   - Validar todos os endpoints
   - Testar health check e métricas
   - Validar tratamento de erros
   - Testar rate limiting
   - Verificar documentação Swagger

4. **Teste E2E Completo:**
   - Executar query completa com client_id C001 via CLI
   - Executar mesmo fluxo via API
   - Validar fluxo completo dos 5 passos em ambos
   - Verificar otimização de custo (pergunta condicional)
   - Analisar logs Chain-of-Thought
   - Comparar métricas entre CLI e API

---

## 📋 Checklist de Implementação

- [ ] Setup de dependências e ambiente
- [ ] Criar estrutura de diretórios
- [ ] Implementar Tool 1 (SQL Runner)
- [ ] Implementar Tool 2 (Brewery Finder)
- [ ] Implementar Tool 3 (Web Explorer)
- [ ] Implementar RAG Manager (FAISS)
- [ ] Implementar Logger estruturado
- [ ] Implementar Planner Agent
- [ ] Implementar lógica condicional (timeout)
- [ ] **Implementar main.py (CLI Conversacional)**
- [ ] **Implementar ChatSession manager**
- [ ] **Implementar API FastAPI completa**
- [ ] **Implementar Session Manager para API**
- [ ] **Implementar Autenticação e Rate Limiting**
- [ ] Testes unitários de cada Tool
- [ ] Testes da interface CLI
- [ ] Testes da API (todos endpoints)
- [ ] Teste E2E completo (CLI + API)
- [ ] **Gerar collection Postman/Insomnia**
- [ ] **Criar documentação de uso (CLI + API)**
- [ ] Otimizar performance e custo

---

## 🚀 Comandos de Execução

### CLI Conversacional (main.py)
```bash
# Modo interativo (padrão)
python main.py

# Com client_id pré-definido
python main.py --client_id C001

# Modo debug (mostra logs detalhados)
python main.py --debug

# Comandos durante execução:
# /exit ou /quit    - Sair do chat
# /clear            - Limpar histórico
# /log              - Mostrar Chain-of-Thought
# /metrics          - Mostrar métricas da sessão
```

### API REST (FastAPI)
```bash
# Desenvolvimento (com auto-reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Produção (múltiplos workers)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Acessar documentação Swagger
open http://localhost:8000/docs

# Acessar ReDoc
open http://localhost:8000/redoc
```

### Exemplo de Uso da API
```python
import requests

# Criar sessão
response = requests.post("http://localhost:8000/chat/session")
session_id = response.json()["session_id"]

# Enviar mensagem
response = requests.post(
    "http://localhost:8000/chat/message",
    json={
        "session_id": session_id,
        "client_id": "C001",
        "message": "Sugira uma nova cervejaria local"
    },
    headers={"X-API-Key": "your-api-key-here"}
)

print(response.json()["response"])
```