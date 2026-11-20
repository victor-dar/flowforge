<p align="center">
  <img src="assets/banner.svg" alt="FlowForge — plataforma para criar assistentes de atendimento" width="100%">
</p>

<p align="center">
  <a href="https://github.com/victor-dar/flowforge/actions/workflows/ci.yml"><img src="https://github.com/victor-dar/flowforge/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/status-MVP%20em%20desenvolvimento-6d5dfc" alt="MVP em desenvolvimento">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-MIT-22a06b" alt="Licença MIT"></a>
</p>

<p align="center">
  <strong>Crie assistentes de atendimento, ensine com seus documentos e publique no seu site.</strong>
</p>

<p align="center">
  <a href="#sobre-o-projeto">Sobre</a> ·
  <a href="#funcionalidades">Funcionalidades</a> ·
  <a href="#início-rápido">Início rápido</a> ·
  <a href="docs/GUIA_USUARIO.md">Guia do usuário</a> ·
  <a href="docs/API.md">API</a>
</p>

## Sobre o projeto

FlowForge é um projeto open source em estágio de MVP para configurar chatbots de atendimento com informações de um negócio e incorporá-los em sites. O repositório contém um painel web em React e TypeScript, uma API em FastAPI e um widget JavaScript.

> **Estado:** funcional para desenvolvimento e demonstração; ainda não recomendado como serviço SaaS de produção. A busca pode combinar resultados lexicais e embeddings opcionais da OpenAI, o armazenamento padrão é SQLite e recursos operacionais e de privacidade ainda precisam evoluir.

## Funcionalidades

- Cadastro, login e gerenciamento isolado de assistentes por usuário.
- Configuração de nome, empresa, instruções, mensagem inicial e cor.
- Upload de documentos PDF, TXT, MD e CSV, com limites configuráveis de tamanho e caracteres.
- Persistência de documentos, conversas e mensagens por assistente.
- Busca híbrida: recuperação lexical local e embeddings opcionais da OpenAI.
- Chunking persistente e histórico limitado nas conversas enviadas ao modelo.
- Domínios autorizados configuráveis por assistente para o widget público.
- Respostas diferentes para saudações e perguntas sem contexto no modo sem provedor de IA.
- Teste de conversa no painel e histórico acessível pela API.
- Widget incorporável em sites por meio de um snippet JavaScript.
- Integração opcional com uma API compatível com OpenAI.
- Limites de requisição para autenticação e chat público.
- Logs estruturados de requisições e endpoint interno de métricas.
- Migrações Alembic e configuração de ambiente de staging.
- Suíte de testes backend e frontend integrada ao CI.

Sem chave de IA, o chat usa recuperação lexical, responde a saudações diretamente e apresenta os trechos encontrados ou informa que não encontrou contexto suficiente. Com `OPENAI_API_KEY`, o RAG pode combinar resultados lexicais com embeddings do modelo configurado. Se o provedor de embeddings falhar, a busca lexical continua como fallback.

## Interface

<p align="center">
  <img src="assets/screenshots/dashboard.png" alt="Visão geral do painel FlowForge" width="82%">
</p>
<p align="center">
  <sub>Painel em estado inicial, sem dados de usuário.</sub>
</p>

<details>
  <summary>Ver tela de acesso</summary>
  <p align="center">
    <img src="assets/screenshots/login.png" alt="Tela de acesso do FlowForge" width="65%">
  </p>
</details>

## Início rápido

### Com Docker Compose

Requer Docker Engine e Docker Compose:

```bash
docker compose up --build
```

Após a inicialização:

| Serviço | Endereço |
|---|---|
| Painel | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Documentação interativa | <http://localhost:8000/docs> |
| Verificação de saúde | <http://localhost:8000/health> |

O Compose usa SQLite e persiste os dados no volume `flowforge_data`. Para usar um provedor de IA, configure `OPENAI_API_KEY` no ambiente antes de iniciar os serviços.

### Execução local

Requer Python 3.11 ou superior, Node.js 22 e npm.

**1. Inicie a API:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**2. Em outro terminal, inicie o painel:**

```bash
cd frontend
npm ci
npm run dev
```

O painel usa `http://localhost:8000` como URL padrão da API. Para apontar a outro endereço, defina `VITE_API_URL` antes de iniciar o Vite ou gerar o build.

Se o painel abrir por `127.0.0.1:5173` ou pelo endereço da rede local, configure essas origens em `CORS_ORIGINS`:

```bash
export CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173,http://192.168.15.8:5173'
```

## Configuração

A API lê configurações do ambiente e de `backend/.env`. As opções disponíveis e seus valores padrão estão em [`backend/.env.example`](backend/.env.example).

Além do limite de upload (`MAX_DOCUMENT_BYTES`, padrão de 5 MB), o texto extraído tem limite de `MAX_DOCUMENT_CHARACTERS` (padrão de 500.000 caracteres). Arquivos que ultrapassarem qualquer limite são rejeitados sem salvar conteúdo parcial.

O RAG combina ranking lexical local com embeddings da OpenAI quando `OPENAI_API_KEY` está configurado. Sem uma chave, a busca continua disponível usando recuperação lexical.

As principais opções relacionadas ao chat e aos documentos são:

| Variável | Padrão | Uso |
|---|---:|---|
| `OPENAI_API_KEY` | vazio | Ativa geração de resposta pelo provedor compatível |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo usado para respostas |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo usado para embeddings |
| `AI_MAX_OUTPUT_TOKENS` | `600` | Limite máximo de tokens de resposta |
| `MAX_DOCUMENT_BYTES` | `5242880` | Tamanho máximo de upload |
| `MAX_DOCUMENT_CHARACTERS` | `500000` | Tamanho máximo do texto extraído |
| `PUBLIC_CHAT_RATE_LIMIT_PER_MINUTE` | `20` | Limite de chat por IP |
| `PUBLIC_CHAT_DAILY_LIMIT_PER_BOT` | `500` | Limite diário por assistente |

Para produção, use `APP_ENV=production`, configure uma `SECRET_KEY` aleatória e exclusiva com pelo menos 32 caracteres, defina origens explícitas em `CORS_ORIGINS` e termine TLS em um proxy/ingress confiável. Não use a chave padrão do Compose. Consulte [Segurança e privacidade](docs/SEGURANCA.md) antes de expor a aplicação.

## Testes

```bash
# Backend
cd backend
pip install -r requirements.txt
pytest -q
```

Em outro terminal, a partir da raiz do repositório:

```bash
cd frontend
npm ci
npm test
npm run build
```

O backend possui testes unitários e de integração para autenticação, privacidade entre assistentes, upload, extração de documentos, chat, rate limiting e avaliação automática do corpus RAG. O frontend possui testes de sessão e interface com Vitest e Testing Library.

O CI executa os testes do backend com Python 3.12, os testes e o build do frontend com Node.js 22 em pushes e pull requests.

### Migrações do banco

O projeto inclui configuração inicial do Alembic:

```bash
cd backend
alembic -c ../alembic.ini upgrade head
```

Para criar uma nova revisão após alterações nos modelos:

```bash
alembic -c ../alembic.ini revision --autogenerate -m "descricao da mudanca"
```

Para desenvolvimento local rápido, o lifespan ainda usa `create_all`. Em produção, use migrações Alembic em vez de depender apenas da criação automática.

### Ambiente de staging

Há uma configuração separada em [`docker-compose.staging.yml`](docker-compose.staging.yml):

```bash
SECRET_KEY='uma-chave-secreta-com-pelo-menos-32-caracteres' \
CORS_ORIGINS='https://painel.exemplo.com' \
docker compose -f docker-compose.staging.yml up --build
```

Defina também `OPENAI_API_KEY` e `VITE_API_URL` quando necessário.

### PostgreSQL

Para iniciar a API, o painel e PostgreSQL 16:

```bash
POSTGRES_PASSWORD='senha-do-banco' \
SECRET_KEY='uma-chave-secreta-com-pelo-menos-32-caracteres' \
CORS_ORIGINS='http://localhost:5173' \
docker compose -f docker-compose.postgres.yml up --build
```

Antes da implantação, execute as migrações:

```bash
DATABASE_URL='postgresql+psycopg://usuario:senha@localhost:5432/flowforge' \
alembic -c alembic.ini upgrade head
```

### Dados de exemplo

Há um conjunto pronto para testar um assistente de cafeteria em [`docs/exemplos/cafe-salvador/`](docs/exemplos/cafe-salvador/):

- `cardapio.txt`: bebidas, comidas, adicionais e formas de pagamento
- `horario-local.txt`: horários e endereço
- `politicas.txt`: cancelamento, troca e reembolso

Esses arquivos podem ser enviados pela aba **Base de conhecimento** e testados pela aba **Testar assistente**.

## Observabilidade

A API registra em JSON o método, caminho, status e duração das requisições. Contagens operacionais ficam disponíveis somente para usuários autenticados em `GET /api/metrics` e `GET /metrics`.

Esse endpoint não substitui métricas, rastreamento distribuído ou monitoramento de erros em produção.

## Limitações atuais

- Embeddings opcionais dependem de um provedor externo; não há OCR ou banco vetorial persistente.
- O painel usa exclusivamente cookie `HttpOnly` com `Secure` e `SameSite=Lax` em produção. Bearer permanece aceita apenas para compatibilidade da API.
- O widget pode restringir origens por assistente, mas a lista não substitui HTTPS e controles de segurança adicionais.
- A allowlist do widget limita o uso público por domínio, mas não autentica visitantes e não substitui autenticação ou mitigação de abuso.
- Sem fila/worker para processar documentos grandes.
- SQLite como banco padrão; carga concorrente e operação de produção não foram validadas.
- Sem confirmação de e-mail, recuperação de senha, cobrança ou métricas de uso completas.
- Políticas de retenção, exportação e exclusão de dados ainda precisam ser definidas.
- O modelo recebe até seis mensagens anteriores da conversa, com limite de 1.000 caracteres por mensagem.

Essas limitações e os próximos passos estão detalhados em [Escopo](docs/ESCOPO.md) e [Roadmap](docs/ROADMAP.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Guia do usuário](docs/GUIA_USUARIO.md) | Cadastro, configuração, documentos, testes e publicação |
| [Referência da API](docs/API.md) | Endpoints, autenticação e exemplos |
| [Arquitetura](docs/ARQUITETURA.md) | Componentes e fluxos atualmente implementados |
| [Escopo](docs/ESCOPO.md) | Estado das funcionalidades e objetivos do MVP |
| [Roadmap](docs/ROADMAP.md) | Evoluções planejadas |
| [Segurança e privacidade](docs/SEGURANCA.md) | Controles, configuração e lacunas conhecidas |
| [Contribuição](CONTRIBUTING.md) | Ambiente, validações e fluxo de pull request |

## Contribuições

Relatos, sugestões e pull requests são bem-vindos. Para mudanças maiores, abra uma issue para discutir a proposta antes de começar. Consulte [`CONTRIBUTING.md`](CONTRIBUTING.md) para instruções.

## Licença

Distribuído sob a licença [MIT](LICENSE).
