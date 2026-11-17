# Segurança e privacidade

Este documento registra controles encontrados no MVP e lacunas conhecidas. Não representa certificação, auditoria independente ou garantia de adequação legal.

## Controles implementados

- Senhas derivadas com PBKDF2-HMAC-SHA256 e comparação resistente a timing.
- Tokens JWT assinados com algoritmo HS256 e prazo de expiração.
- Rotas privadas verificam usuário autenticado; operações de chatbot restringem por proprietário.
- Upload restringe formatos, tamanho e conteúdo textual vazio.
- Limites para autenticação por IP, chat por IP e chat por chatbot, armazenados no banco.
- Inicialização em produção rejeita a chave padrão/exemplo e CORS wildcard.
- Chave do provedor de IA lida no backend, não enviada como dado do painel/widget.

## Configuração segura

1. Use `APP_ENV=production`.
2. Gere `SECRET_KEY` aleatória, exclusiva, com pelo menos 32 caracteres; armazene-a em secret manager.
3. Configure `CORS_ORIGINS` somente com origens necessárias. CORS não substitui autenticação nem validação de origem do widget.
4. Use HTTPS no proxy/ingress; encaminhe IP real somente por proxies explicitamente confiáveis.
5. Proteja o arquivo de banco e seus backups; defina retenção, acesso e criptografia adequados ao ambiente.
6. Não registre tokens, chaves, mensagens ou conteúdo documental sem necessidade definida.
7. Monitore limites e gastos do provedor: a cota atual conta mensagens, não valor monetário.

## Lacunas e riscos conhecidos

- Não há allowlist de domínios por chatbot. Rotas públicas podem ser chamadas fora do widget.
- `visitor_id` identifica a conversa, mas não é uma credencial forte; não deve ser tratado como autenticação.
- Não há recuperação de senha, verificação de e-mail, MFA ou fluxo de exclusão de conta.
- Não há política de retenção, exportação, consentimento do visitante ou aviso de privacidade implementados.
- Proteções contra prompt injection não são garantidas. Documentos e mensagens devem ser considerados conteúdo não confiável.
- Extração de PDF não é sandbox isolada; revisite limites de CPU/memória e bibliotecas antes de operar com uploads públicos.
- Rate limit usa janela fixa e banco; não substitui proteção de borda, monitoramento ou mitigação distribuída.
- O frontend guarda o JWT em `localStorage`, o que aumenta o impacto de uma vulnerabilidade XSS.
- SQLite e `create_all` não fornecem, por si sós, estratégia de migração, alta disponibilidade ou operação concorrente.

## Privacidade e LGPD

Antes de uso comercial, definir finalidade e base legal, aviso de privacidade para operadores e visitantes, retenção, exclusão, atendimento a direitos dos titulares, suboperadores (incluindo provedor de IA), transferências internacionais e resposta a incidentes com assessoria adequada.

## Relato de vulnerabilidades

Não publique dados pessoais, segredos nem detalhes exploráveis em issues públicas. Contate os mantenedores por canal privado do repositório, com passos de reprodução seguros e impacto observado.
