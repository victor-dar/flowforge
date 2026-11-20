# Referência da API

A especificação OpenAPI interativa gerada pelo FastAPI está disponível em `/docs` quando a API está em execução. As rotas abaixo refletem os endpoints registrados em `backend/app/main.py`.

## Convenções

- JSON em requisições/respostas, exceto upload de documento (`multipart/form-data`).
- Rotas de conta e gerenciamento exigem `Authorization: Bearer <token>`, salvo quando indicado como pública.
- Erros usam o formato padrão do FastAPI (`{"detail": ...}`).
- Tipos e limites de campos estão definidos em `backend/app/schemas.py`.

## Saúde e widget

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/health` | Público | Verificação básica de processo; não verifica banco/provedor |
| `GET` | `/metrics` ou `/api/metrics` | Autenticado | Contagens básicas de usuários, assistentes, documentos e conversas |
| `GET` | `/widget.js` | Público | Script incorporável |
| `GET` | `/widget` | Público | Página do iframe |

## Autenticação

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/auth/register` | Criar usuário e emitir JWT (`201`) |
| `POST` | `/api/auth/login` | Validar credenciais e emitir JWT |
| `GET` | `/api/auth/me` | Retornar o usuário autenticado |
| `POST` | `/api/auth/logout` | Remover o cookie de autenticação |

Exemplo:

```http
POST /api/auth/register
Content-Type: application/json

{"email":"pessoa@exemplo.com","password":"uma-senha-segura"}
```

Resposta de sucesso contém `access_token`, `token_type` e `user`. Senhas devem ter entre 8 e 128 caracteres.

## Assistentes

Todas as rotas exigem JWT:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/bots` | Listar assistentes do usuário |
| `POST` | `/api/bots` | Criar assistente (`201`) |
| `GET` | `/api/bots/{bot_id}` | Obter assistente próprio |
| `PATCH` | `/api/bots/{bot_id}` | Atualizar campos fornecidos |
| `DELETE` | `/api/bots/{bot_id}` | Excluir assistente e dados relacionados (`204`) |
| `GET` | `/api/bots/{bot_id}/documents` | Listar documentos |
| `POST` | `/api/bots/{bot_id}/documents` | Enviar documento (`201`) |
| `DELETE` | `/api/bots/{bot_id}/documents/{document_id}` | Excluir documento (`204`) |
| `GET` | `/api/bots/{bot_id}/conversations` | Listar até 100 conversas e mensagens |

`BotCreate` e `BotUpdate` aceitam nome, empresa, descrição, instruções, boas-vindas e cor hexadecimal. Extensões aceitas para documentos: PDF, TXT, MD e CSV. O upload padrão limita os bytes a 5 MB (`MAX_DOCUMENT_BYTES`) e o texto extraído a 500.000 caracteres (`MAX_DOCUMENT_CHARACTERS`). Ultrapassar um limite retorna `413` e não persiste documento parcial; arquivo sem texto ou falha de extração retorna `422`.

## Rotas públicas de chat

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/public/bots/{bot_id}` | Dados públicos mínimos do assistente |
| `POST` | `/api/public/bots/{bot_id}/chat` | Criar/continuar conversa (`200`) |

Exemplo de requisição:

```json
{
  "message": "Quais são os horários?",
  "visitor_id": "id-do-visitante",
  "conversation_id": null
}
```

Resposta de sucesso:

```json
{
  "conversation_id": 42,
  "answer": "..."
}
```

Para continuar, envie o mesmo `visitor_id` com o `conversation_id` retornado. Sem autenticação pública, esses identificadores não são segredo ou prova de identidade. O provedor de IA indisponível retorna `503` com `Retry-After`; limites atingidos retornam `429`.

## Limites e segurança

Os valores padrão são configurados no ambiente. Janelas são fixas e os contadores persistem no banco. O endpoint `/health` apenas indica que o processo responde; não deve ser usado como health check completo de dependências em produção.
