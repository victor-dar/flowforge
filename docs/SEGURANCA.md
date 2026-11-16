# Segurança e Privacidade — FlowForge

A plataforma armazenará informações comerciais e conversas de usuários finais. Segurança é requisito fundamental desde a primeira versão.

## Princípios

- Cada chatbot acessa **somente** os dados e documentos autorizados pelo seu proprietário
- Menor privilégio por padrão
- Dados sensíveis nunca expostos ao frontend ou ao widget

## Checklist de requisitos

- [ ] Isolamento dos dados de cada usuário (relacional e vetorial)
- [ ] Autenticação segura (hash de senha forte, tokens com expiração)
- [ ] Controle de permissões
- [ ] Proteção de credenciais e chaves de API (variáveis de ambiente / cofre de segredos)
- [ ] Validação de arquivos enviados (tipo, tamanho, conteúdo)
- [ ] Limites de utilização por usuário e por chatbot
- [ ] Proteção contra abuso dos endpoints (rate limit, validação de origem do widget)
- [ ] Controle de acesso ao histórico de conversas
- [ ] Políticas de retenção e exclusão de dados
- [ ] Adequação à LGPD (base legal, consentimento, direitos do titular, aviso de privacidade)

## Considerações específicas de IA

- Mitigar prompt injection (separar instruções do sistema e conteúdo do usuário)
- Não expor instruções internas do bot a visitantes
- Registrar uso para controle de custo e auditoria

## Pontos a definir

- Política de retenção padrão das conversas
- Fluxo de exclusão de conta e dados
- Aviso ao visitante final de que está conversando com uma IA
