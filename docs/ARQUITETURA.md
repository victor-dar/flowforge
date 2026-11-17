# Arquitetura do FlowForge

Este documento descreve o código implementado no repositório hoje. Componentes planejados para versões futuras aparecem como evolução, não como parte do runtime atual.

## Visão geral

```mermaid
flowchart LR
  Browser[React + TypeScript] -->|HTTP/JSON, JWT| API[FastAPI]
  Site[Site externo] -->|widget.js| Widget[Script do widget]
  Widget -->|iframe| API
  API --> DB[(SQLite padrão / SQLAlchemy)]
  API -->|opcional| LLM[API compatível com OpenAI]
  API -->|extração + busca lexical| Docs[Documentos do chatbot]
```

![Diagrama da arquitetura](../assets/architecture.svg)

## Componentes implementados

| Componente | Localização | Responsabilidade |
|---|---|---|
| Painel | `frontend/src/` | Autenticação, gerenciamento de assistentes, configuração, upload, teste e snippet do widget |
| API | `backend/app/main.py` | Rotas HTTP, autenticação/autorização, persistência, upload e chat |
| Modelos | `backend/app/models.py` | Usuários, chatbots, documentos, conversas, mensagens e buckets de rate limit |
| Provedor de IA e busca | `backend/app/ai.py` | Recuperação lexical e chamada opcional ao endpoint compatível com OpenAI |
| Widget | `backend/app/widget.js`, `backend/app/widget_page.py` | Botão incorporável e interface de conversa em iframe |
| Banco | SQLAlchemy | SQLite por padrão; URL configurável |

## Fluxo de autenticação e gerenciamento

1. O painel envia credenciais à API.
2. A senha é derivada com PBKDF2-HMAC-SHA256; a API retorna um JWT Bearer.
3. Rotas privadas validam o token e associam as operações ao usuário autenticado.
4. As consultas de chatbot verificam a propriedade antes de retornar ou alterar dados.

## Fluxo de mensagem

1. O painel ou widget envia `message`, `visitor_id` e, em mensagens seguintes, `conversation_id`.
2. A API valida o chatbot e confirma que uma conversa fornecida pertence àquele chatbot e visitante.
3. Limites por IP e chatbot são contabilizados no banco.
4. A API procura trechos de texto lexicalmente relevantes nos documentos do chatbot.
5. Se `OPENAI_API_KEY` estiver configurada, envia instruções, contexto recuperado e pergunta ao modelo configurado. Caso contrário, responde com o contexto recuperado ou uma mensagem de falta de informação.
6. Mensagem e resposta são persistidas e a resposta retorna ao cliente.

O mecanismo atual não envia histórico anterior como contexto do LLM, não usa embeddings e não deve ser descrito como RAG vetorial.

## Fluxo de documentos

1. Um usuário autenticado envia PDF, TXT, MD ou CSV para um chatbot que possui.
2. A API limita o tamanho, extrai texto (PDF via `pypdf`; demais formatos como UTF-8) e rejeita conteúdo vazio.
3. O texto extraído é persistido no banco relacional.
4. Na solicitação de chat, a busca divide texto por pontuação/quebras de linha, pontua sobreposição de palavras e seleciona trechos.

Não há fila/worker, OCR, embeddings ou banco vetorial nesta versão.

## Persistência e consistência

SQLAlchemy é a camada de persistência. A configuração padrão utiliza SQLite local; Docker Compose persiste o arquivo em volume. Não há migrações configuradas no repositório; a inicialização cria tabelas ausentes usando `Base.metadata.create_all`.

SQLite/PostgreSQL são os dialetos explicitamente suportados pelo rate limiter. A URL pode ser alterada, mas outros dialetos não são compatíveis com esse recurso no código atual.

## Widget incorporável

O snippet carrega `widget.js` com `data-bot-id`. O script cria um botão e um iframe apontando para a página do widget servida pela API. A página consulta as rotas públicas do chatbot.

Exemplo:

```html
<script
  src="https://api.exemplo.com/widget.js"
  data-bot-id="123"
  defer
></script>
```

Substitua domínio e ID pelos valores do seu ambiente. O endpoint público não verifica uma lista de domínios permitidos por chatbot no estado atual.

## Implantação

Docker Compose oferece API e frontend e um volume SQLite para desenvolvimento/demonstração. Para produção, são necessários, no mínimo, planejamento de banco, migrações, segredo e CORS de produção, proxy/HTTPS, backups, logs/monitoramento e política de retenção. PostgreSQL, filas, cache e busca vetorial permanecem opções de evolução, não dependências atuais.
