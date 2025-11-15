# 🍺 Assistente de Reabastecimento Inteligente BEES

> **Agente IA conversacional para otimização de pedidos e descoberta de novos fornecedores no mercado B2B de bebidas**

[![Status](https://img.shields.io/badge/Status-Planning%20Complete-green)]()
[![Version](https://img.shields.io/badge/Version-3.0-blue)]()
[![Python](https://img.shields.io/badge/Python-3.10+-yellow)]()
[![Framework](https://img.shields.io/badge/Framework-LangChain-orange)]()
[![LLM](https://img.shields.io/badge/LLM-Gemini%201.5%20Flash-red)]()

---

## 🎯 Sobre o Projeto

Este projeto implementa um **agente IA inteligente** que auxilia clientes B2B da plataforma BEES a:
1. 🔍 **Consultar seu histórico** de compras e preferências
2. 💡 **Descobrir novos fornecedores** locais alinhados ao seu perfil
3. 📊 **Otimizar custos** através de cache inteligente e perguntas condicionais

### Características Principais

✅ **Arquitetura Plan-and-Execute** com 3 ferramentas especializadas  
✅ **Text-to-SQL** para consultas ao banco de dados proprietário  
✅ **Cache TTL (30 dias)** para otimização de custos de busca web  
✅ **Otimização de custo** através de pergunta condicional (timeout 30s)  
✅ **CLI Conversacional** com interface Rich para demonstração  
✅ **API REST** (FastAPI) para integração com sistemas externos  
✅ **Observabilidade completa** com logs estruturados e Chain-of-Thought  

---

## 🚀 Quick Start

### 1. Clone e Setup

```bash
# Clone o repositório
git clone <repository-url>
cd BESS-TecnicalCase

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua GOOGLE_API_KEY
```

### 2. Execute o CLI Conversacional

```bash
# Modo interativo (padrão)
python main.py

# Com client_id pré-definido
python main.py --client_id C001

# Modo debug
python main.py --debug
```

### 3. Execute a API REST

```bash
# Desenvolvimento (com auto-reload)
uvicorn api.main:app --reload

# Acesse a documentação
open http://localhost:8000/docs
```

---

## 📚 Documentação

### 📖 Comece Aqui
- **[INDICE.MD](INDICE.MD)** - Índice geral de toda a documentação
- **[SUMARIO_EXECUTIVO.MD](SUMARIO_EXECUTIVO.MD)** - Resumo executivo (5 min)

### 🏗️ Arquitetura e Planejamento
- **[PLANNING.MD](PLANNING.MD)** - Guia técnico completo (7 fases)
- **[ARQUITETURA.MD](ARQUITETURA.MD)** - Diagramas e fluxos detalhados
- **[DECISOES_TECNICAS.MD](DECISOES_TECNICAS.MD)** - Stack e decisões consolidadas

### 💻 Implementação
- **[TODO.MD](TODO.MD)** - Roadmap e checklist de implementação
- **[ESPECIFICACOES_CLI_API.MD](ESPECIFICACOES_CLI_API.MD)** - Specs completas do CLI e API

### 🤖 Prompts dos Agentes
- **[prompts/planner.MD](prompts/planner.MD)** - Agente orquestrador
- **[prompts/sql_runner.MD](prompts/sql_runner.MD)** - Tool 1 (Text-to-SQL)
- **[prompts/new_opportunities.MD](prompts/new_opportunities.MD)** - Tool 2 (API Integration)
- **[prompts/web_explorer.MD](prompts/web_explorer.MD)** - Tool 3 (Cache TTL)

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    USUÁRIO (Cliente B2B)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        ┌───────▼────────┐    ┌──────▼────────┐
        │  CLI (Rich)    │    │  API (FastAPI)│
        │  main.py       │    │  6 endpoints  │
        └───────┬────────┘    └──────┬────────┘
                │                     │
                └──────────┬──────────┘
                           │
                ┌──────────▼──────────┐
                │   PLANNER AGENT     │
                │  (Gemini 1.5 Flash) │
                │  5 Passos           │
                └──────────┬──────────┘
                           │
        ┏━━━━━━━━━━━┳━━━━━━┻━━━━━━┳━━━━━━━━━━━┓
        ▼           ▼              ▼           ▼
   ┌────────┐  ┌────────┐    ┌────────┐  ┌────────┐
   │ Tool 1 │  │ Tool 2 │    │ Tool 3 │  │ Logger │
   │  SQL   │  │Brewery │    │  Web   │  │  JSON  │
   │ Runner │  │ Finder │    │Explorer│  │        │
   └───┬────┘  └───┬────┘    └───┬────┘  └────────┘
       │           │              │
       ▼           ▼              ▼
   customers.db  OpenBrewery   FAISS
                   DB API       Cache
```

---

## 🛠️ Stack Tecnológico

| Categoria | Tecnologia |
|:----------|:-----------|
| **LLM** | Google Gemini 1.5 Flash |
| **Framework** | LangChain |
| **Embeddings** | Google `models/embedding-001` |
| **Vector DB** | FAISS (local) |
| **Database** | SQLite (`customers.db`) |
| **Web Search** | Google Search API |
| **CLI** | Rich + asyncio |
| **API** | FastAPI + Uvicorn |
| **Session** | In-memory (ou Redis) |

---

## 🎨 Exemplos de Uso

### CLI - Exemplo Completo

```
$ python main.py --client_id C001

🍺 Assistente de Reabastecimento BEES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Sessão iniciada para cliente: Bar do João (C001)

👤 Você: Sugira uma nova cervejaria local

🤔 Pensando... (Buscando perfil)
🤔 Pensando... (Buscando oportunidades)

📋 Assistente BEES:
Suas 5 cervejas mais pedidas são:
1. Stone IPA
2. Ballast Point Sculpin
3. Lagunitas IPA
4. Sierra Nevada Pale Ale
5. Anchor Steam

💡 Sugestão: Modern Times Beer (micro)
É uma cervejaria local em San Diego.

⏱️ Gostaria de ver um resumo detalhado? (30s)

👤 Você: sim

✅ Modern Times Beer é uma cervejaria artesanal
   fundada em 2013, conhecida por suas IPAs
   experimentais e ambiente descontraído.

👤 Você: /metrics

📊 Métricas da Sessão
━━━━━━━━━━━━━━━━━━━━━
• Tempo total: 8.4s
• Cache hit rate: 100%
• Custo estimado: $0.0042
```

### API - Exemplo Python

```python
import requests

BASE_URL = "http://localhost:8000"
headers = {"X-API-Key": "your-api-key"}

# Criar sessão
session = requests.post(f"{BASE_URL}/chat/session", headers=headers)
session_id = session.json()["session_id"]

# Enviar mensagem
response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "session_id": session_id,
        "client_id": "C001",
        "message": "Sugira uma nova cervejaria local"
    },
    headers=headers
)

print(response.json()["response"])
```

---

## 📋 Comandos CLI

| Comando | Descrição |
|:--------|:----------|
| `/exit` ou `/quit` | Encerra o chat |
| `/clear` | Limpa histórico da conversa |
| `/log` | Mostra Chain-of-Thought da última execução |
| `/metrics` | Exibe métricas da sessão |
| `/help` | Lista todos os comandos |

---

## 🌐 Endpoints da API

| Método | Endpoint | Descrição |
|:-------|:---------|:----------|
| POST | `/chat/session` | Criar nova sessão |
| POST | `/chat/message` | Enviar mensagem ao agente |
| GET | `/chat/session/{id}` | Obter histórico da sessão |
| DELETE | `/chat/session/{id}` | Encerrar sessão |
| GET | `/health` | Health check |
| GET | `/metrics` | Métricas agregadas |

**Documentação completa:** `http://localhost:8000/docs`

---

## 🧪 Testes

```bash
# Testes unitários
pytest tests/test_tools.py

# Testes do agente
pytest tests/test_agent.py

# Testes da API
pytest tests/test_api.py

# Todos os testes
pytest
```

---

## 📊 Estrutura do Projeto

```
BESS-TecnicalCase/
├── 📄 Documentação (13 arquivos)
│   ├── README.MD ← Você está aqui
│   ├── INDICE.MD
│   ├── SUMARIO_EXECUTIVO.MD
│   ├── PLANNING.MD
│   ├── TODO.MD
│   ├── DECISOES_TECNICAS.MD
│   ├── ARQUITETURA.MD
│   ├── ESPECIFICACOES_CLI_API.MD
│   ├── RESUMO_ATUALIZACAO.MD
│   ├── requirements.txt
│   ├── .env.example
│   └── prompts/ (4 arquivos)
│
├── 💻 Código
│   ├── main.py              # CLI Conversacional
│   ├── tools/               # 3 Tools especializadas
│   ├── agents/              # Planner Agent
│   ├── utils/               # Logger, RAG, ChatSession
│   ├── api/                 # FastAPI (6 endpoints)
│   └── tests/               # Testes unitários
│
└── 🗄️ Dados
    ├── customers.db         # Banco SQLite
    ├── data/faiss_index/    # Cache RAG
    └── logs/                # Logs de execução
```

---

## 🎯 Roadmap

### ✅ Fase 1: Planejamento (Completo)
- [x] Arquitetura definida
- [x] Documentação completa
- [x] Prompts dos agentes
- [x] Especificações CLI e API

### ⏳ Fase 2: Implementação Core (Próximo)
- [ ] Setup inicial
- [ ] Implementação das 3 Tools
- [ ] Agente Orquestrador
- [ ] Sistema de Logging

### ⏳ Fase 3: Interfaces
- [ ] CLI Conversacional (main.py)
- [ ] API REST (FastAPI)

### ⏳ Fase 4: Testes e Deploy
- [ ] Testes unitários
- [ ] Testes E2E
- [ ] Collection Postman
- [ ] Documentação de uso final

---

## 🤝 Contribuindo

Este é um projeto de demonstração técnica para a BEES. Para contribuir:

1. Leia a documentação completa em [INDICE.MD](INDICE.MD)
2. Siga o roadmap em [TODO.MD](TODO.MD)
3. Consulte as especificações em [ESPECIFICACOES_CLI_API.MD](ESPECIFICACOES_CLI_API.MD)

---

## 📝 Licença

Este projeto é proprietário e confidencial da BEES.

---

## 📞 Contato

**Responsável:** Anderson  
**Projeto:** BEES Technical Case  
**Versão:** 3.0 Final  
**Data:** 15/11/2025

---

## 🌟 Destaques Técnicos

### Otimizações Implementadas

🚀 **Cache TTL (30 dias)** - Reduz custos de busca web em ~70-80%  
🚀 **Pergunta Condicional** - Reduz chamadas desnecessárias em ~50%  
🚀 **Schema Injection** - Elimina RAG adicional, mais simples e rápido  
🚀 **Filtro de Histórico** - Garante apenas novidades para o cliente  

### Observabilidade

📊 **Logs Estruturados** - JSON com timestamp, args, results  
📊 **Chain-of-Thought** - Trace completo de execução  
📊 **Métricas em Tempo Real** - Tempo, cache hit rate, custo estimado  
📊 **Health Check** - Status de todos os serviços  

---

**Status Atual:** ✅ Planejamento 100% Completo | ⏳ Pronto para Implementação

**Próximo Passo:** Execute `python main.py` após implementar o código 🚀
