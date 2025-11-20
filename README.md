# BeerForYou - Assistente de Recomendações Personalizadas

Sistema de recomendação de cervejarias baseado em IA conversacional que combina dados de clientes com informações públicas para sugerir novas cervejarias personalizadas.

## Características Principais

- Interface CLI conversacional com contexto persistente
- Análise de perfil de cliente via Text-to-SQL
- Busca de cervejarias na OpenBreweryDB API
- Exploração web com RAG e cache para otimização de custos
- Arquitetura Plan-and-Execute com LangChain e Gemini 2.5 Flash

## Tecnologias

- **LLM:** Gemini 2.5 Flash (Google AI)
- **Framework:** LangChain
- **Vector Store:** FAISS
- **Database:** SQLite
- **API Externa:** OpenBreweryDB


## Estrutura do Projeto

```
.
├── agents/              # Agente planner (orquestrador)
├── tools/               # Tools (SQL, Brewery Finder, Web Explorer)
├── utils/               # Utilitários (sessão, RAG, prompts)
├── data/                # Banco de dados e índice FAISS
├── prompts/             # Templates de prompts
├── docs/                # Documentação técnica detalhada
├── main.py              # CLI conversacional
└── requirements.txt     # Dependências
```

## Documentação

Para informações detalhadas, consulte:

- [TUTORIAL_USO.md](docs/TUTORIAL_USO.md) - Guia completo de uso
- [GUIA_TECNICO.md](docs/GUIA_TECNICO.md) - Documentação técnica e arquitetura
- [DESIGN_ESCALA.md](docs/DESIGN_ESCALA.md) - Estratégias de escalabilidade
- [OpenBreweryDB API.md](docs/OpenBreweryDB%20API.md) - Referência da API externa

## Sobre o Autor

- Nome: **Anderson Luiz Souza**

- LinkedIn: https://www.linkedin.com/in/andluizsouza/

- GitHub: https://github.com/andluizsouza 
