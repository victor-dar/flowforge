# Roadmap

O roadmap separa o que já existe no código do trabalho recomendado. Prioridades podem mudar conforme feedback de usuários. O estado atual das funcionalidades está detalhado em [Escopo](ESCOPO.md).

## P0 — Preparar para validação com usuários

- [x] Fluxo básico de conta e assistentes
- [x] Upload de conhecimento e teste de chat
- [x] Widget incorporável
- [x] Testes automatizados iniciais e CI
- [x] Histórico limitado enviado ao modelo
- [x] Chunking e embeddings persistidos por documento
- [x] Domínio permitido por chatbot
- [x] Migrações de banco com Alembic
- [x] Observabilidade inicial com logs JSON e métricas
- [ ] Completar visualização e gerenciamento de documentos no painel
- [ ] Adicionar fluxo guiado de configuração e checklist de publicação
- [ ] Exibir erros, limites e estado do serviço com feedback consistente
- [ ] Validar acessibilidade e layout em dispositivos móveis

## P1 — Confiabilidade e segurança operacional

- [ ] Definir política de retenção, exportação e exclusão de dados
- [ ] Migrar autenticação persistente para cookies HttpOnly/Secure/SameSite
- [ ] Recuperação de senha e verificação de e-mail
- [ ] Migrações PostgreSQL validadas em staging
- [ ] Alertas, rastreamento distribuído e SLOs
- [ ] Testes de concorrência e de integração em ambiente implantado
- [ ] Rever segurança de upload e limites de recursos com threat model

## P2 — Qualidade de respostas e escala

- [ ] Expandir avaliação automática da busca lexical e semântica
- [ ] Migrar embeddings para banco vetorial adequado
- [ ] Abstrair provedores e registrar consumo/tokens
- [ ] Avaliar PostgreSQL para persistência de produção
- [ ] Processamento assíncrono para documentos grandes, se a demanda justificar

## P3 — Produto SaaS

- [ ] Métricas de conversas e uso precisas
- [ ] Administração de contas e suporte
- [ ] Planos, limites e faturamento
- [ ] Integrações priorizadas por entrevistas com usuários
- [ ] Recursos de agência/equipe somente após validar demanda
