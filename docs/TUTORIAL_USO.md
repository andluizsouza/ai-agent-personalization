# Tutorial: Como Usar o Agente BeerForYou

Este tutorial fornece instruções passo-a-passo para configurar e usar o assistente de IA conversacional para consulta de dados e recomendação personalizadas.

---

## Pré-requisitos

Antes de começar, certifique-se de ter:

- **Python 3.13** instalado no seu sistema
- **Git** (para clonar o repositório)
- **Conexão com a internet** (para instalação de dependências e uso da API)
- **Chave da API do Google Gemini** (gratuita)

---

## Instalação e Configuração

### Passo 1: Clonar o Repositório

```bash
git clone https://github.com/andluizsouza/ai-agent-personalization.git
cd ai-agent-personalization
```

### Passo 2: Criar Ambiente Virtual (Python 3.13)

É altamente recomendado usar um ambiente virtual para isolar as dependências do projeto.

#### No Linux/Mac:

```bash
# Criar ambiente virtual com Python 3.13
python3.13 -m venv venv

# Ativar o ambiente virtual
source venv/bin/activate
```

#### No Windows:

```bash
# Criar ambiente virtual com Python 3.13
python -m venv venv

# Ativar o ambiente virtual
venv\Scripts\activate
```

Após ativar o ambiente virtual, você verá `(venv)` no início do prompt do terminal.

### Passo 3: Instalar Dependências

Com o ambiente virtual ativado, instale todas as dependências necessárias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

As principais dependências incluem:
- **LangChain**: Framework para construção de aplicações com LLMs
- **Google Generative AI**: API do Google Gemini
- **FAISS**: Banco de dados vetorial para cache
- **SQLAlchemy**: ORM para banco de dados SQL
- **Rich**: Interface CLI aprimorada

### Passo 4: Configurar Chave da API do Google

#### 4.1. Obter Chave da API

1. Acesse: [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Faça login com sua conta Google
3. Clique em "**Get API Key**" ou "**Create API Key**"
4. Copie a chave gerada (formato: `AIza...`)

#### 4.2. Configurar a Chave no Projeto

Crie um arquivo `.env` na raiz do projeto:

```bash
# Criar arquivo .env
touch .env
```

Adicione a seguinte linha ao arquivo `.env`:

```env
GOOGLE_API_KEY=sua_chave_api_aqui
```

**Exemplo:**
```env
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**IMPORTANTE**: Nunca compartilhe sua chave de API publicamente ou faça commit dela no Git!

### Passo 5: Criar o Banco de Dados Local

O projeto utiliza um banco de dados SQLite local com informações simuladas de clientes e histórico de compras.

```bash
# Executar script de criação do banco
python data/create_database.py
```

Este script irá:
- Criar o arquivo `customers.db` com 20 clientes fictícios dentro da pasta `data/`
- Gerar histórico de compras aleatório
- Popular dados de preferências e perfis de clientes
---

## Como Usar o Agente CLI

### Iniciar o Agente

#### Modo Interativo Básico:

```bash
python main.py
```

### Interface do CLI

Ao iniciar, você verá uma tela de boas-vindas apresentando as capacidades do agente:

```
╔════════════════════════════════════════════════════════════════╗
║     BeerForYou - Assistente de Recomendações Personalizadas    ║
╚════════════════════════════════════════════════════════════════╝

Olá! Bem-vindo ao seu assistente pessoal de cervejarias.                                                                

Estou aqui para ajudar você a descobrir novas cervejarias locais personalizadas de acordo com suas preferências.  
```

---

## Exemplos de Perguntas

O agente BeerForYou é capaz de responder diversos tipos de perguntas usando três ferramentas principais. Abaixo estão exemplos organizados por categoria.

### 1. Consultas ao Perfil do Cliente

Estas perguntas usam a ferramenta **get_client_profile** para buscar informações básicas do perfil:

```
Você: Quais são minhas cervejarias favoritas?

Você: Mostre meus top 5 produtos

Você: Quais tipos de cervejarias eu prefiro?

Você: Qual minha localização cadastrada?
```

### 2. Consultas Analíticas sobre Seus Próprios Dados

Estas perguntas usam a ferramenta **run_analytical_query** para análises sobre seus dados pessoais:

```
Você: Qual cerveja eu mais compro?

Você: Quais são minhas cervejarias favoritas com mais detalhes?

Você: Qual é o tipo de cervejaria que eu mais compro?
```

### 3. Consultas Estatísticas Agregadas (Sem Dados Individuais)

Perguntas sobre estatísticas gerais usando **run_analytical_query**:

```
Você: Qual a cerveja mais comprada no estado da Califórnia?

Você: Quantos clientes preferem cervejarias do tipo micro?

Você: Qual o tipo de cervejaria mais popular no Ohio?

Você: Quantos clientes existem no estado de Oregon?

Você: Quais são as cervejas AB-InBev mais populares?

Você: Qual a distribuição de clientes por tipo de cervejaria favorita?
```

### 4. Descoberta de Novas Cervejarias

Estas perguntas usam a ferramenta **search_breweries_by_location_and_type** para encontrar novas cervejarias:

```
Você: Encontre cervejarias em San Diego que eu ainda não conheço

Você: Quais cervejarias micro existem em Portland, Oregon?

Você: Me mostre brewpubs em Austin, Texas

Você: Encontre cervejarias artesanais em Denver

Você: Quero conhecer novas cervejarias locais em Seattle

Você: Mostre cervejarias regionais em Fort Collins

Você: Descubra novas cervejarias para mim em Boston
```

### 5. Informações Sobre Cervejarias Específicas

Buscar informações detalhadas de cervejarias conhecidas:

```
Você: Me dê informações sobre a Stone Brewing

Você: Qual o endereço da Ballast Point?

Você: A Dogfish Head tem website?

Você: Informações de contato da Sierra Nevada

Você: Qual o tipo da cervejaria Russian River?

Você: Onde fica a Modern Times Beer?
```

### 6. Recomendações Personalizadas

Perguntas que combinam múltiplas ferramentas para recomendações baseadas no seu perfil:

```
Você: Baseado no meu histórico, que cervejarias você recomendaria?

Você: Sugira cervejarias próximas que combinam com minhas preferências

Você: Encontre novas cervejarias do mesmo tipo que eu costumo comprar

Você: Quais cervejarias locais vendem estilos parecidos com os que eu gosto?

Você: Recomende fornecedores novos baseado no meu perfil

Você: Preciso expandir meus fornecedores, o que você sugere?
```

### 7. Explorações com Detalhes (Requer Confirmação)

Para obter informações detalhadas sobre uma cervejaria específica, o agente perguntará se você deseja buscar informações online (otimização de custo):

```
Você: Me conte mais sobre a história da Stone Brewing
[Agente perguntará: "Deseja que eu busque informações online?"]

Você: Quais são os diferenciais da Russian River?
[Aguarda sua confirmação para buscar detalhes]

Você: O que torna a Dogfish Head especial?
[Solicitará permissão antes de buscar na web]
```

---

## Client IDs para Testes

O banco de dados foi criado com 20 clientes fictícios baseados em cervejarias reais. Aqui estão alguns client_ids que você pode usar para testar o sistema:

| Client ID | Nome/Empresa | Localização | Tipo Principal |
|-----------|--------------|-------------|----------------|
| `CLT-HNG179` | 10 Barrel Brewing Co | Bend, Oregon | large |
| `CLT-OMA295` | Against the Grain Brewery | Louisville, Kentucky | brewpub |
| `CLT-LYO494` | Ballast Point Brewing Company | San Diego, California | large |
| `CLT-MOD205` | Brooklyn Brewery | Brooklyn, New York | regional |
| `CLT-NYR204` | Deschutes Brewery | Bend, Oregon | regional |
| `CLT-CIR456` | Dogfish Head Craft Brewery | Milton, Delaware | regional |
| `CLT-VYT050` | Founders Brewing Co | Grand Rapids, Michigan | regional |
| `CLT-GCG585` | Great Lakes Brewing Company | Cleveland, Ohio | regional |
| `CLT-WSD650` | Lagunitas Brewing Company | Petaluma, California | regional |
| `CLT-UDT589` | New Belgium Brewing Company | Fort Collins, Colorado | regional |

---

## Entendendo o Comportamento do Agente

### Arquitetura Plan-and-Execute

O agente usa uma arquitetura inteligente com três ferramentas especializadas:

1. **Tool 1A - get_client_profile**: Busca perfil básico do cliente
2. **Tool 1B - run_analytical_query**: Executa consultas analíticas com proteção de privacidade
3. **Tool 2 - search_breweries_by_location_and_type**: Busca cervejarias por localização e tipo
4. **Tool 3 - get_website_summary**: Obtém informações detalhadas (com confirmação do usuário)

### Proteção de Privacidade

O agente implementa regras rígidas de privacidade:

**PERMITIDO**:
- Seus próprios dados: "Quais cervejas EU compro?"
- Estatísticas agregadas: "Qual a cerveja mais popular no estado?"

**BLOQUEADO**:
- Dados de outros clientes: "O que o cliente X compra?"
- Informações individuais de terceiros

