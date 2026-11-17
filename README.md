<p align="center">
  <img src="assets/banner.svg" alt="FlowForge" width="100%">
</p>

<p align="center">
  <img alt="Status" src="https://img.shields.io/badge/status-MVP%20funcional-blue">
  <img alt="Licença" src="https://img.shields.io/badge/licen%C3%A7a-MIT-green">
  <img alt="Frontend" src="https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-61dafb">
  <img alt="Backend" src="https://img.shields.io/badge/backend-FastAPI-009688">
</p>

# FlowForge

> **Sua ideia. Sua inteligência. Sua automação.**

FlowForge é um MVP para criar chatbots com base de conhecimento, testar respostas e publicar um widget em sites. O repositório contém uma interface React, uma API FastAPI e persistência SQLAlchemy.

## Funcionalidades implementadas

- Cadastro e login com senha armazenada usando PBKDF2-HMAC-SHA256 e tokens JWT Bearer com expiração.
- Isolamento de chatbots por usuário e gerenciamento dos próprios bots.
- Upload e exclusão de documentos PDF, TXT, MD e CSV; extração e recuperação lexical simples de trechos.
- Chat público com histórico de conversas e widget incorporável.
- Integração opcional com a API de chat da OpenAI. Sem chave configurada, a API responde usando o conteúdo recuperado da base.
- SQLite como banco padrão local e no Docker Compose.

Este é um MVP, não um serviço SaaS pronto para produção: a recuperação de documentos é lexical (não usa embeddings/vetores), e ainda faltam controles como rate limiting, cotas e administração de contas.

## Rodar localmente

Requisitos: Python 3.12+, Node.js 22+ e npm.

1. Configure e execute a API:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   uvicorn app.main:app --reload
   ```

   A API fica em `http://localhost:8000`; verificação de saúde: `/health`, documentação interativa: `/docs`.

2. Em outro terminal, execute a interface:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   A interface fica em `http://localhost:5173`. Configure `VITE_API_URL` se a API estiver em outro endereço.

## Docker Compose

Na raiz do repositório:

```bash
docker compose up --build
```

O Compose inicia API e frontend nas portas 8000 e 5173 e persiste os dados SQLite no volume `flowforge_data`. Para substituir os valores locais, defina `SECRET_KEY`, `OPENAI_API_KEY` e `OPENAI_MODEL` no ambiente ou em um arquivo `.env` na raiz. O valor local de `SECRET_KEY` do Compose não deve ser usado em produção.

## Configuração e produção

`backend/.env.example` documenta as variáveis da API. Para desenvolvimento, `DATABASE_URL` usa `sqlite:///./flowforge.db`; `CORS_ORIGINS` aceita uma lista de origens separadas por vírgula. A configuração padrão local não exige chave OpenAI.

Em produção:

- Defina `APP_ENV=production`.
- Configure `SECRET_KEY` com pelo menos 32 caracteres, aleatória e exclusiva; a API rejeita a chave padrão e o valor de exemplo.
- Configure `CORS_ORIGINS` somente com origens explícitas; origem wildcard é rejeitada.
- Use armazenamento e backups adequados ao ambiente. SQLite atende ao desenvolvimento/MVP; avalie um banco gerenciado para produção.
- Armazene chaves em um gerenciador de segredos e configure HTTPS no proxy/ingress.

A API valida a configuração de produção durante a inicialização. Não publique o arquivo `.env` nem credenciais.

## Testes e CI

Os testes do backend usam SQLite isolado em memória:

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

O workflow [CI](.github/workflows/ci.yml) executa os testes do backend com Python 3.12 e o build do frontend com Node 22 em pushes e pull requests.

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Escopo](docs/ESCOPO.md)
- [Roadmap](docs/ROADMAP.md)
- [Segurança e privacidade](docs/SEGURANCA.md)
- OpenAPI local: `http://localhost:8000/docs`

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).
