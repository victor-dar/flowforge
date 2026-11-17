# Roadmap

O roadmap separa o que já existe no código do trabalho recomendado. Prioridades podem mudar conforme feedback de usuários. O estado atual das funcionalidades está detalhado em [Escopo](ESCOPO.md).

## P0 — Preparar para validação com usuários

- [x] Fluxo básico de conta e assistentes
- [x] Upload de conhecimento e teste de chat
- [x] Widget incorporável
- [x] Testes automatizados iniciais e CI
- [ ] Completar visualização e gerenciamento de documentos no painel
- [ ] Adicionar fluxo guiado de configuração e checklist de publicação
- [ ] Exibir erros, limites e estado do serviço com feedback consistente
- [ ] Validar acessibilidade e layout em dispositivos móveis

## P1 — Confiabilidade e segurança operacional

- [ ] Definir política de retenção, exportação e exclusão de dados
- [ ] Validação de origem/domínio do widget por chatbot
- [ ] Recuperação de senha e verificação de e-mail
- [ ] Migrações de banco de dados versionadas
- [ ] Observabilidade: logs estruturados, métricas e alertas
- [ ] Testes de concorrência e de integração em ambiente implantado
- [ ] Rever segurança de upload e limites de recursos com threat model

## P2 — Qualidade de respostas e escala

- [ ] Avaliar busca lexical com conjunto de perguntas real
- [ ] Implementar chunking e recuperação semântica com índices adequados
- [ ] Adicionar histórico ao contexto da conversa de forma controlada
- [ ] Abstrair provedores e registrar consumo/tokens
- [ ] Avaliar PostgreSQL para persistência de produção
- [ ] Processamento assíncrono para documentos grandes, se a demanda justificar

## P3 — Produto SaaS

- [ ] Métricas de conversas e uso precisas
- [ ] Administração de contas e suporte
- [ ] Planos, limites e faturamento
- [ ] Integrações priorizadas por entrevistas com usuários
- [ ] Recursos de agência/equipe somente após validar demanda
