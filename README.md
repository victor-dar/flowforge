# FlowForge

**Crie, configure e publique assistentes de atendimento para o seu negócio.**

FlowForge é um MVP open source de uma plataforma para criar chatbots com uma base de conhecimento e publicá-los em sites por meio de um widget incorporável. O repositório reúne um painel web em React/TypeScript e uma API em FastAPI.

> **Estado do produto:** MVP funcional em desenvolvimento. A aplicação já permite criar conta, gerenciar assistentes, carregar documentos, testar o chat e incorporar o widget. Ainda não é um SaaS pronto para produção: a busca de conhecimento é lexical, o banco padrão é SQLite e faltam recursos de operação, privacidade e administração.

## Visão rápida

| Área | Implementação atual |
|---|---|
| Painel | React, TypeScript e Vite |
| API | Python, FastAPI, Pydantic e SQLAlchemy |
| Persistência padrão | SQLite |
| Autenticação | Senhas com PBKDF2-HMAC-SHA256 e JWT Bearer |
| Conhecimento | Extração de PDF/TXT/MD/CSV e busca lexical simples |
| Provedor de IA | API compatível com OpenAI, opcional |
| Widget | JavaScript que incorpora um iframe hospedado pela API |
| Testes | Pytest para API e build/type-check do frontend |

![Tela de acesso](assets/screenshots/login.png)

![Visão geral do painel em estado vazio](assets/screenshots/dashboard.png)

*Capturas reais do frontend local; a visão geral mostra o estado vazio, sem dados de usuário.*

## O que já é possível fazer

- Criar uma conta e entrar no painel.
- Criar, editar e excluir assistentes.
- Personalizar instruções, mensagem inicial e cor.
- Carregar documentos PDF, TXT, Markdown e CSV (limite padrão de 5 MB por arquivo).
- Testar conversas pelo painel e consultar o histórico pela API.
- Publicar o chat em outro site com um snippet JavaScript.
- Usar limites de requisições para autenticação e chat público.
- Executar sem chave de IA: nesse modo, o chat retorna trechos recuperados dos documentos ou uma resposta informando que não há contexto.

## Capturas

As imagens em [`assets/screenshots/`](assets/screenshots/) mostram a interface da versão atual. Podem ser atualizadas quando o painel mudar.

## Começar localmente

### Requisitos

- Python 3.11 ou superior
- Node.js 22 e npm

### API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API: <http://localhost:8000>

Saúde: <http://localhost:8000/health>

Documentação interativa: <http://localhost:8000/docs>

### Painel

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Painel: <http://localhost:5173>

O painel usa `http://localhost:8000` por padrão. Para outra URL, configure `VITE_API_URL` antes de iniciar/buildar o frontend.

### Docker Compose

Na raiz do repositório:

```bash
docker compose up --build
```

O Compose publica o painel na porta 5173 e a API na 8000, e armazena o SQLite no volume `flowforge_data`. As imagens atuais precisam das dependências listadas nos Dockerfiles. Para configurar provedores ou ambiente, defina as variáveis descritas em [`backend/.env.example`](backend/.env.example) e no `docker-compose.yml`.

## Configuração

As configurações da API são lidas de variáveis de ambiente e do arquivo `backend/.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_ENV` | `development` | Defina `production` para ativar validações de inicialização |
| `DATABASE_URL` | `sqlite:///./flowforge.db` | URL SQLAlchemy |
| `SECRET_KEY` | chave de desenvolvimento | Assinatura dos JWTs e chaves de rate limit |
| `ACCESS_TOKEN_MINUTES` | `1440` | Validade do token de acesso |
| `CORS_ORIGINS` | `http://localhost:5173` | Origens permitidas, separadas por vírgula |
| `OPENAI_API_KEY` | vazio | Habilita chamadas ao provedor compatível com OpenAI |
| `OPENAI_BASE_URL` | endpoint OpenAI | Endpoint compatível com `/chat/completions` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo solicitado |
| `MAX_DOCUMENT_BYTES` | `5242880` | Tamanho máximo do arquivo enviado |
| `AUTH_RATE_LIMIT_PER_MINUTE` | `10` | Tentativas por IP em janela de minuto |
| `PUBLIC_CHAT_RATE_LIMIT_PER_MINUTE` | `20` | Mensagens por IP em janela de minuto |
| `PUBLIC_CHAT_DAILY_LIMIT_PER_BOT` | `500` | Mensagens por chatbot em janela de 24 horas |
| `AI_MAX_OUTPUT_TOKENS` | `600` | Limite de tokens de saída (máximo configurável: 4000) |

Em produção, defina `APP_ENV=production`, use uma chave aleatória exclusiva com pelo menos 32 caracteres, configure origens CORS explícitas, HTTPS, armazenamento/backups apropriados e um banco suportado para carga esperada. Não use valores de exemplo ou a chave local do Compose.

Mensagens são limitadas a 4000 caracteres pelo schema da API. O campo `MAX_MESSAGE_LENGTH` ainda não está conectado a essa validação; alterá-lo não muda o limite efetivo.

## Testes e qualidade

Backend:

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

O workflow de CI executa os testes do backend com Python 3.12 e o build do frontend com Node 22 em pushes e pull requests.

## Documentação

- [Guia do usuário](docs/GUIA_USUARIO.md)
- [Referência da API](docs/API.md)
- [Arquitetura atual](docs/ARQUITETURA.md)
- [Escopo e estado do MVP](docs/ESCOPO.md)
- [Roadmap](docs/ROADMAP.md)
- [Segurança e privacidade](docs/SEGURANCA.md)
- [Como contribuir](CONTRIBUTING.md)

## Limitações conhecidas

- A recuperação de documentos é lexical, sem embeddings, ranking semântico ou banco vetorial.
- SQLite é adequado para desenvolvimento e demonstração; não foi validado para concorrência/carga de produção.
- O painel ainda não oferece administração de contas, cobrança, métricas reais ou gestão de retenção.
- A criação de conta não possui confirmação de e-mail nem recuperação de senha.
- O widget público não aplica validação de origem por chatbot; CORS da API é a configuração global atual.
- A extração de PDF não processa OCR para documentos digitalizados.
- Integrações de CRM, WhatsApp, agendamento e atendimento humano não estão implementadas.

## Licença

MIT. Consulte [`LICENSE`](LICENSE).
