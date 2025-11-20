# GUIA TÉCNICO - BeerForYou: Recomendações Personalizadas


## Sumário

1. [Visão Geral da Arquitetura](#1-visao-geral-da-arquitetura)
2. [Tool 1: SQL Runner - Text-to-SQL com Segurança](#2-tool-1-sql-runner)
3. [Tool 2: Brewery Finder - Integração OpenBreweryDB](#3-tool-2-brewery-finder)
4. [Tool 3: Web Explorer - RAG Cache com Gemini Grounding](#4-tool-3-web-explorer)
5. [Planner Agent - Orquestrador Inteligente](#5-planner-agent)
6. [Decisões Técnicas e Trade-offs](#6-decisões-técnicas-e-trade-offs)


---

## 1. Visão Geral da Arquitetura

### 1.1 Pattern Arquitetural: Plan-and-Execute Agent

O sistema implementa o pattern **Plan-and-Execute** usando LangChain e Gemini 2.5 Flash com function calling. Este pattern separa:

- **Planning (Planejamento):** O agente Planner define o plano de 5 passos
- **Execution (Execução):** Cada tool é executada sequencialmente conforme o plano
- **Conditional Logic (Lógica Condicional):** Tool 3 só é executada se usuário confirmar interesse

### 1.2 Fluxo de Execução Completo

```
Usuário Requisita Recomendação
         |
         v
   Planner Agent (Gemini 2.5 Flash)
         |
         v
    [Passo 1] Tool 1: SQL Runner
         |
         v
    get_client_profile(client_id) --> Retorna perfil completo
         |
         v
    [Passo 2] Tool 2: Brewery Finder
         |
         v
    search_breweries(city, state, type, history) --> Retorna novas cervejarias
         |
         v
    [Passo 3] Apresentacao Inicial
         |
         v
    "Gostaria de saber mais detalhes?" (Otimizacao de Custo)
         |
         v
    [Passo 4] Espera Resposta Usuário (30s timeout)
         |
         +---> SIM: [Passo 5] Tool 3: Web Explorer
         |           |
         |           v
         |     get_website_summary() --> Cache ou Grounding
         |
         +---> NÃO: Termina (economia de custos)
```

### 1.3 Stack Tecnológico

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| LLM | Gemini 2.5 Flash | Melhor custo-benefício (0.075/1M input, 0.30/1M output) |
| Embeddings | Google Embedding-001 | Gratuito até 1500 req/minuto |
| Vector Store | FAISS | Open-source, rápido, sem custos de infraestrutura |
| Database | SQLite | Leve, sem servidor, suficiente para protótipo |
| Framework | LangChain | Function calling nativo, integração fácil |
| API Externa | OpenBreweryDB | Gratuita, sem autenticação, dados públicos |

---

## 2. Tool 1: SQL Runner

### 2.1 Objetivo

Recuperar informações do cliente do banco de dados `data/customers.db` usando **Text-to-SQL** com Gemini 2.5 Flash, implementando camadas rigorosas de segurança e privacidade.

### 2.2 Funcionalidades Principais

#### 2.2.1 Função Principal: `get_client_profile()`

Busca perfil completo do cliente com lógica de fallback:

1. **Busca primária:** Por `client_id` (identificador único)
2. **Fallback:** Por `postal_code` + `client_name` (busca combinada)
3. **Retorno:** Perfil completo ou `not_found`

**Dados Retornados:**
```python
{
    "client_id": "C001",
    "client_name": "Bar do Joao",
    "client_location_city_state": "San Diego, CA",
    "postal_code": "92101",
    "top3_brewery_types": ["micro", "brewpub", "regional"],
    "top5_beers_recently": ["IPA", "Pale Ale", ...],
    "top3_breweries_recently": ["Stone Brewing", ...],
    "brewery_history": ["Stone Brewing", "Ballast Point", ...],
    "search_metadata": {...}
}
```

#### 2.2.2 Função Analítica: `run_analytical_query()`

Executa queries analíticas/estatísticas com proteção de privacidade rigorosa.

**Regras de Privacidade:**

| Tipo de Query | Permitido? | Exemplo |
|---------------|------------|---------|
| Dados próprios | SIM | "Quais cervejas EU compro mais?" |
| Dados de outros | NÃO | "Qual a cervejaria favorita do cliente X?" |
| Agregados/Estatísticas | SIM | "Qual a cerveja mais vendida em Ohio?" |

**Mecanismo de Validação:**
1. Detecta queries agregadas (COUNT, AVG, GROUP BY)
2. Bloqueia referências a `client_id` de outros clientes
3. Permite apenas dados do cliente autenticado ou agregados

### 2.3 Arquitetura de Segurança (READ-ONLY MODE)

#### 2.3.1 Camada 1: Validação de Keywords

```python
FORBIDDEN_KEYWORDS = [
    'insert', 'update', 'delete', 'drop', 'truncate', 'alter',
    'create', 'replace', 'rename', 'grant', 'revoke',
    'attach', 'detach', 'pragma'
]
```

**Função:** `_validate_read_only(sql_query)`

**Verificações:**
1. Query deve começar com `SELECT`
2. Nenhuma keyword proibida presente
3. Detecção de SQL injection multi-statement (`;` seguido de comando proibido)

#### 2.3.2 Camada 2: Prompt Engineering

O prompt de geração SQL inclui instruções explícitas:

```
CRITICAL SECURITY RULES:
1. Generate ONLY SELECT queries
2. NEVER generate INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE
3. Use parameterized queries when possible
4. Always include LIMIT clause for safety
```

### 2.4 Text-to-SQL com Gemini

**Processo:**

1. **Prompt Template Carregado:** `prompts/sql_generation.txt`
2. **Schema Injetado:** `prompts/customers_schema.txt` (estrutura das tabelas)
3. **Geração SQL:** Gemini 2.5 Flash gera query baseada em linguagem natural
4. **Limpeza:** Remove markdown code blocks (```sql)
5. **Validação:** Checa segurança antes de executar
6. **Execução:** sqlite3 com row_factory para conversão automática
7. **Parsing JSON:** Converte campos JSON (top3_brewery_types, etc.)

### 2.5 Decisões Técnicas

#### Por que Gemini 2.5 Flash para SQL?

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Modelo | Gemini 2.5 Flash | 10x mais barato que GPT-4o, performance similar |
| Temperature | 0 | Determinístico - crítico para SQL |
| Fallback | Lógica de busca múltipla | Tolerância a falhas, UX melhorada |
| Schema External | Arquivo separado | Facilita manutenção, versionamento |

#### Trade-offs

**SEGURANÇA vs FLEXIBILIDADE**
- **Escolha:** Segurança máxima (read-only)
- **Sacrifício:** Não pode fazer updates via linguagem natural
- **Justificativa:** Em produção, dados sensíveis de clientes não devem ser alterados pelo agente

**CUSTO vs LATÊNCIA**
- **Escolha:** Cache não implementado (queries rápidas)
- **Justificativa:** SQLite local é extremamente simples e rápido para protótipos. Mas para projetos reais, o banco dever estar em produção em uma infra dedicada; e com mais controles de acesso e segurança (ex: _disaster recovery_, _row-level security_)

---

## 3. Tool 2: Brewery Finder

### 3.1 Objetivo

Buscar cervejarias na **OpenBreweryDB API** filtrando aquelas que o cliente já comprou, garantindo recomendações sempre novas e relevantes.

### 3.2 Fluxo de Execução

```
Input: city, state, brewery_type, brewery_history
   |
   v
[Passo 1] Validação de Parâmetros
   |
   v
[Passo 2] Chamada API OpenBreweryDB
   |        - by_city: San Diego
   |        - by_state: california
   |        - by_type: micro
   |        - per_page: 50
   v
[Passo 3] Filtragem de Histórico
   |        - Normaliza nomes (lowercase, strip)
   |        - Remove breweries em brewery_history
   v
[Passo 4] Formatação de Resultados
   |        - Estrutura completa com todos os campos
   v
Output: Lista de cervejarias novas + metadata
```

### 3.3 Lógica de Filtragem Inteligente

#### 3.3.1 Normalização de Nomes

**Problema:** API pode retornar "Stone Brewing Company" enquanto histórico tem "Stone Brewing"

**Solução:** `_simplify_brewery_name()`

```python
# Remove sufixos comuns para matching robusto
suffixes = [
    " brewing company",
    " brewing co",
    " brewery",
    " brewing", 
    " brewpub",
    " co"
]
```

**Exemplo:**
- Input: "Stone Brewing Company"
- Output: "stone"
- Compara com historico: "stone" == "stone" (match)

#### 3.3.2 Validação de Novidade

**Função:** `_is_brewery_new()`

1. Normaliza nome da cervejaria
2. Normaliza todo o histórico
3. Verifica se nome não está em histórico
4. Retorna True/False

### 3.4 Integração OpenBreweryDB API

#### 3.4.1 Especificações da API

- **URL Base:** `https://api.openbrewerydb.org/v1/breweries`
- **Autenticação:** Nenhuma (pública)
- **Rate Limit:** Não documentado, mas generoso
- **Timeout:** 10s (configurável)
- **Resultados por página:** 50 (max configurável)

#### 3.4.2 Mapeamento de Estados

```python
STATE_MAP = {
    "CA": "california",
    "NY": "new_york",
    "TX": "texas",
    # ... 50 estados
}
```

**Motivo:** API aceita nomes completos com underscore, não códigos.

#### 3.4.3 Parâmetros de Busca

| Parâmetro | Formato API | Exemplo |
|-----------|-------------|---------|
| city | by_city | `san_diego` |
| state | by_state | `california` |
| type | by_type | `micro` |
| name | by_name | `stone` |

### 3.5 Formato de Resposta Completo

```python
{
    # Identificação
    "brewery_id": "5494",
    "brewery_name": "Stone Brewing",
    "brewery_type": "regional",
    
    # Endereço (estruturado)
    "address_1": "1999 Citracado Pkwy",
    "address_2": None,
    "address_3": None,
    "street": "1999 Citracado Pkwy",
    "city": "Escondido",
    "state": "California",
    "state_province": "California",
    "postal_code": "92029-1113",
    "country": "United States",
    
    # Contato
    "phone": "7607968585",
    "website_url": "http://www.stonebrew.com",
    
    # Localização
    "latitude": "33.1260526",
    "longitude": "-117.1290906"
}
```

**Campos "Unavailable":** Se API não retornar, preenche com string "Unavailable" (não None).

### 3.6 Decisões Técnicas

#### Por que OpenBreweryDB?

| Aspecto | Vantagem |
|---------|----------|
| Custo | 100% gratuito, sem API key |
| Cobertura | 8000+ cervejarias nos EUA |
| Dados | Endereço completo, coordenadas, website |
| Confiabilidade | API estável, mantida pela comunidade |
| Latência | ~200-500ms por request |

#### Trade-offs

**CUSTO vs DADOS ATUALIZADOS**
- **Escolha:** API gratuita pública
- **Sacrifício:** Dados podem estar desatualizados
- **Mitigação:** Tool 3 valida websites via Grounding (dados atuais)

**SIMPLICIDADE vs CONTROLE**
- **Escolha:** API externa (não scraping)
- **Vantagem:** Zero manutenção, sem quebrar com mudanças em sites
- **Limitação:** Dependente da disponibilidade da API

---

## 4. Tool 3: Web Explorer

### 4.1 Objetivo

Obter resumos detalhados de websites de cervejarias usando **estratégia de cache RAG com TTL** e fallback com **Gemini Grounding (Google Search)**, para otimizar custos.

### 4.2 Arquitetura de Cache Inteligente

```
Request: get_website_summary(brewery_name, url)
   |
   v
[Camada 1] RAG Cache (FAISS)
   |
   +---> CACHE_HIT (< 30 dias)
   |     |
   |     v
   |   Return cached summary (CUSTO ZERO)
   |
   +---> CACHE_MISS / CACHE_STALE (> 30 dias)
         |
         v
      [Camada 2] Gemini Grounding (Google Search)
         |
         v
      Gera novo resumo via Google Search
         |
         v
      [Camada 3] Atualiza Cache
         |
         v
      Salva FAISS index em disco
         |
         v
      Return novo resumo
```

### 4.3 RAG Manager - Cache com TTL

#### 4.3.1 Estrutura do Cache

**Vector Store:** FAISS (Facebook AI Similarity Search)
- Embeddings: Google Embedding-001 (gratuito)
- Index persistido em: `data/faiss_index/`
- Busca por similaridade semântica

**Metadata por Documento:**
```python
{
    "brewery_name": "Stone Brewing",
    "url": "http://stonebrew.com",
    "summary": "Stone Brewing e uma...",
    "creation_date": "2025-11-20T10:30:00",
    "brewery_type": "regional"
}
```

#### 4.3.2 Lógica de TTL (Time-to-Live)

**Configuração:** 30 dias (configurável)

**Validação:**
```python
def _is_entry_stale(creation_date: str) -> bool:
    created = datetime.fromisoformat(creation_date)
    age_days = (datetime.now() - created).days
    return age_days > ttl_days
```

**Estados de Cache:**
- `CACHE_HIT`: Entrada encontrada e válida (< 30 dias)
- `CACHE_STALE`: Entrada encontrada mas expirada (> 30 dias)
- `CACHE_MISS`: Nenhuma entrada encontrada

### 4.4 Gemini Grounding - Google Search Integration

#### 4.4.1 O que é Gemini Grounding?

**Definição:** Feature nativa do Gemini que permite pesquisar Google Search durante geração, retornando informações atualizadas e referenciadas.

**Vantagens sobre Web Scraping:**
- Sempre atualizado (busca em tempo real)
- Não quebra com mudanças em HTML
- Respeita robots.txt e restrições
- Qualidade de busca do Google
- Menos manutenção

#### 4.4.2 Implementação Técnica

```python
from google import genai
from google.genai import types

# Configurar grounding
grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool],
    temperature=0
)

# Gerar com grounding
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=config
)
```

#### 4.4.3 Prompt Template

**Arquivo:** `prompts/web_explorer.txt`

**Estrutura:**
```
Busque informações atualizadas sobre a cervejaria:

Nome: {brewery_name}
Endereço: {address}
Website: {url}

Gere um resumo de até 3 frases cobrindo:
1. Especialidade (tipos de cerveja, estilo)
2. Diferenciais (prêmios, história única, etc.)
3. Experiência (tour, taproom, eventos)

Use Google Search para informações precisas e atuais.
```

#### 4.4.4 Metadata de Grounding

**Informações Retornadas:**
- `web_search_queries`: Queries usadas pelo Gemini
- `grounding_chunks`: Número de fontes consultadas
- `grounding_support`: Nível de confiança das informações

**Logging:**
```python
if metadata.web_search_queries:
    logger.info(f"Queries: {metadata.web_search_queries}")
if metadata.grounding_chunks:
    logger.info(f"Fontes: {len(metadata.grounding_chunks)}")
```

### 4.5 Decisões Técnicas



#### Trade-offs de TTL

**30 dias escolhido porque:**
- Informações de cervejarias mudam lentamente
- Equilíbrio entre atualização e economia
- 90% hit rate é aceitável

**Alternativas consideradas:**
- 7 dias: Muito frequente, baixo hit rate (70%)
- 90 dias: Alto hit rate (97%), mas dados podem estar desatualizados
- Sem TTL: Perigoso, dados obsoletos permanentemente

---

## 5. Planner Agent

### 5.1 Objetivo

Orquestrar as 3 ferramentas em um **workflow inteligente de 5 passos** usando Gemini 2.5 Flash com _function calling_, implementando lógica condicional para otimização de custos.

### 5.2 Arquitetura do Agente

```
PlannerAgent
   |
   +-- LLM: Gemini 2.5 Flash (temperature=0)
   |
   +-- Tools: [get_client_profile_tool, 
   |           run_analytical_query_tool,
   |           search_breweries_tool, 
   |           get_website_summary_tool]
   |
   +-- Prompt: ChatPromptTemplate (system + human + scratchpad)
   |
   +-- Agent: create_tool_calling_agent() [LangChain]
   |
   +-- Executor: AgentExecutor (max_iterations=10)
```

### 5.3 Plano de 5 Passos (Hard-coded via Prompt)

#### Passo 1: Recuperar Perfil do Cliente

```
Tool: get_client_profile_tool(client_id)

Input: client_id do usuário autenticado
Output: Perfil completo com localização, preferências, histórico

Uso no Planner:
- Extrai city, state para busca geográfica
- Extrai top3_brewery_types para filtro de tipo
- Extrai brewery_history para evitar duplicatas
```

#### Passo 2: Buscar Novas Cervejarias

```
Tool: search_breweries_tool(city, state, brewery_type, brewery_history)

Input: Dados extraídos do perfil
Output: Lista de cervejarias novas (não no histórico)

Lógica:
- Usa brewery_type do top3 (ex: "micro")
- Filtra com brewery_history completo
- Retorna top 3-5 recomendações
```

#### Passo 3: Apresentação Inicial

```
Não é tool, é geração de texto pelo LLM

Output: Mensagem estruturada
"Encontrei X cervejarias novas para voce:
1. [Nome] - [Tipo] - [Cidade, Estado]
2. [Nome] - [Tipo] - [Cidade, Estado]
..."
```

#### Passo 4: Pergunta Condicional (Otimização de Custo)

```
Não é tool, é interação com usuário

Pergunta: "Gostaria de saber mais detalhes sobre alguma dessas cervejarias?"

Timeout: 30 segundos
Opções:
- SIM/Nome da cervejaria: Prossegue para Passo 5
- NÃO/Timeout: Termina (economia de 1-3 requests de Grounding)
```

#### Passo 5: Detalhes Completos (Condicional)

```
Tool: get_website_summary_tool(brewery_name, url, brewery_type, address)

Input: Cervejaria escolhida pelo usuário
Output: Resumo detalhado via cache ou Grounding

Condicional: Executado APENAS se usuário confirmar interesse
Economia: ~60-80% de redução de calls para Tool 3
```

### 5.4 Function Calling com LangChain

#### 5.4.1 Registro de Tools

```python
@tool
def get_client_profile_tool(client_id: str) -> str:
    """
    Retrieve client profile from database.
    
    Args:
        client_id: The unique client identifier
    
    Returns:
        JSON string with client profile
    """
    # Implementação...
```

**LangChain converte automaticamente:**
- Docstring vira descrição da função
- Type hints viram schema de parâmetros
- Return type vira formato de saída

#### 5.4.2 Formato de Function Calling (Gemini)

**Request para Gemini:**
```json
{
  "contents": "Client ID: C001. Execute o plano completo.",
  "tools": [
    {
      "function_declarations": [
        {
          "name": "get_client_profile_tool",
          "description": "Retrieve client profile from database",
          "parameters": {
            "type": "object",
            "properties": {
              "client_id": {"type": "string"}
            },
            "required": ["client_id"]
          }
        }
      ]
    }
  ]
}
```

**Response de Gemini:**
```json
{
  "candidates": [{
    "content": {
      "parts": [{
        "functionCall": {
          "name": "get_client_profile_tool",
          "args": {"client_id": "C001"}
        }
      }]
    }
  }]
}
```

### 5.5 Chain-of-Thought Logging

#### 5.5.1 Estrutura de Log

```python
self.execution_log.append({
    "tool": "get_client_profile",
    "timestamp": "2025-11-20T10:30:15",
    "input": {"client_id": "C001"},
    "execution_time_ms": 234.5,
    "status": "success",
    "cache_status": "N/A"  # Apenas Tool 3
})
```

#### 5.5.2 Métricas Agregadas

**Função:** `get_metrics()`

```python
{
    "total_execution_time_s": 3.45,
    "total_tool_calls": 5,
    "tools_breakdown": {
        "get_client_profile": 1,
        "search_breweries": 1,
        "get_website_summary": 3
    },
    "cache_hit_rate": 0.67,  # 2/3 hits
    "avg_tool_execution_time_ms": 690.0
}
```

### 5.6 Gestão de Contexto e Histórico

#### 5.6.1 Formato de Chat History

```python
chat_history = [
    {"role": "user", "content": "Oi, quero recomendação"},
    {"role": "assistant", "content": "Claro! Qual seu client_id?"},
    {"role": "user", "content": "CLT-LNU555"}
]
```

#### 5.6.2 Conversão para LangChain Messages

```python
from langchain_core.messages import HumanMessage, AIMessage

formatted_history = []
for msg in chat_history:
    if msg["role"] == "user":
        formatted_history.append(HumanMessage(content=msg["content"]))
    elif msg["role"] == "assistant":
        formatted_history.append(AIMessage(content=msg["content"]))
```

#### 5.6.3 Prompt Template com Histórico

```python
prompt = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", f"{system_prompt}\n\n{{input}}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])
```

**agent_scratchpad:** onde Gemini registra function calls intermediários

### 5.7 Decisões Técnicas

#### Por que LangChain em vez de Raw Gemini SDK?

| Aspecto | LangChain | Raw SDK |
|---------|-----------|---------|
| Function Calling | Automático (@tool) | Manual (JSON schemas) |
| Histórico | MessagesPlaceholder | Conversão manual |
| Retry Logic | Built-in | Implementar do zero |
| Logging | Verbose mode | Logging customizado |
| Curva de aprendizado | Media | Baixa |

**Escolha:** LangChain - redução de 60% de código boilerplate

---

## 6. Decisões Técnicas e Trade-offs

### 6.1 Segurança

#### 6.1.1 SQL Injection Prevention

**Layers de Proteção:**

1. **Keyword Blacklist:** Bloqueia INSERT, UPDATE, DELETE, DROP, etc.
2. **Query Start Validation:** Apenas SELECT permitido
3. **Multi-statement Detection:** Bloqueia `; DELETE FROM ...`
4. **LLM Prompt Engineering:** Instruções explícitas para gerar apenas SELECT
5. **Logging Completo:** Todas queries logadas para auditoria

**Nível de Segurança:** ALTO - múltiplas camadas redundantes

**Limitação Conhecida:** LLM pode gerar SQL ineficiente (ex: SELECT * sem LIMIT)

**Mitigação Futura:** Adicionar timeout de query + LIMIT automático

#### 6.1.2 Privacy Protection

**Regras Implementadas:**

| Tipo de Acesso | Proteção | Mecanismo |
|----------------|----------|-----------|
| Dados próprios | PERMITIDO | Valida authenticated_client_id |
| Dados de outros | BLOQUEADO | Detecta client_id != authenticated |
| Agregados | PERMITIDO | Detecta COUNT/AVG/GROUP BY |

**Nível de Privacidade:** MÉDIO - proteção básica implementada

**Limitação Conhecida:** LLM pode usar JOIN para inferir dados de outros
**Mitigação Futura:** Parse AST do SQL para validar JOINs e subqueries

#### 6.1.3 API Security

**OpenBreweryDB:**
- Nenhuma autenticação necessária (dados públicos)
- Rate limiting não documentado
- **Risco:** BAIXO - dados não sensíveis

**Gemini Grounding:**
- API key via environment variable
- Não exposta em logs ou respostas


### 6.2 Manutenibilidade

#### 6.2.1 Separação de Escopos em Módulos

```
/tools/          -> Ferramentas isoladas, testáveis
/agents/         -> Lógica de orquestração
/utils/          -> Funções compartilhadas
/prompts/        -> Templates externos (fácil de iterar)
/data/           -> Persistência (DB + FAISS)
```

**Vantagem:** Cada tool pode ser testada independentemente

#### 6.5.2 Configuração

**Variáveis de Ambiente:**
```
GOOGLE_API_KEY=xxx
DATABASE_PATH=data/customers.db
FAISS_INDEX_PATH=data/faiss_index
CACHE_TTL_DAYS=30
```

**External Prompts:**
```
/prompts/planner.txt
/prompts/sql_generation.txt
/prompts/web_explorer.txt
```

**Vantagem:** Mudar comportamento sem alterar código-fonte

#### 6.5.3 Logging e Observabilidade

**Levels de Logging:**
- INFO: Tool executions, API calls, cache hits
- WARNING: Cache misses, API slowdowns
- ERROR: Tool failures, validation errors

**Métricas Trackeadas:**
- execution_time_ms (por tool)
- cache_hit_rate (Tool 3)
- tool_calls_count (Planner)

**Chain-of-Thought Export:** JSON completo de execução para debugging

---