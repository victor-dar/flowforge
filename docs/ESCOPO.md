# Escopo do Projeto — FlowForge

> Documento inicial. Será aprofundado nas próximas iterações.

## 1. Visão

Plataforma SaaS no-code que permite a qualquer pessoa criar, configurar, personalizar e publicar um chatbot com IA, sem conhecimento técnico.

## 2. Objetivos

- Reduzir a barreira de custo e complexidade para automatizar atendimento
- Oferecer criação guiada em poucos passos
- Permitir que o usuário controle e altere seu próprio assistente
- Validar o produto com uma versão gratuita antes de monetizar

## 3. Público-alvo

**Principal:** pequenos negócios (clínicas, salões, restaurantes, lojas, academias, escolas, escritórios), profissionais autônomos (dentistas, psicólogos, advogados, consultores, personal trainers, designers) e empreendedores iniciantes.

**Secundário:** agências de marketing, profissionais de automação, freelancers, consultorias de tecnologia.

## 4. Escopo do MVP

### Incluído

| # | Funcionalidade | Descrição resumida |
|---|---|---|
| 1 | Cadastro e autenticação | Conta individual, login, recuperação de senha |
| 2 | Dashboard | Visão geral dos chatbots e do uso |
| 3 | Gestão de chatbots | Criar, editar, ativar/desativar, excluir |
| 4 | Configuração guiada | Wizard com perguntas simples; IA gera as instruções do bot |
| 5 | Personalização | Nome, avatar, tom, boas-vindas, regras, cores |
| 6 | Provedor de IA | Integração com um LLM via camada independente de provedor |
| 7 | Base de conhecimento (RAG) | Upload de PDF/TXT e perguntas e respostas |
| 8 | Ambiente de testes | Chat de teste dentro do painel |
| 9 | Widget incorporável | Snippet de código para colar no site |
| 10 | Histórico de conversas | Sessões, mensagens, data/hora, indicadores básicos |
| 11 | Controle de uso | Limites do plano gratuito |

### Fora do MVP

- Integração com WhatsApp
- Integração com CRM e sistemas de agendamento
- Webhooks e APIs externas
- Encaminhamento para atendimento humano
- Editor visual de fluxos
- Gestão de equipes e múltiplos clientes (agências)
- Cobrança e planos pagos

## 5. Fluxo principal do usuário

1. Cria conta → 2. Acessa o painel → 3. Cria chatbot → 4. Informa dados do negócio → 5. Configura comportamento → 6. Adiciona documentos → 7. Testa → 8. Personaliza → 9. Publica → 10. Acompanha conversas e uso

## 6. Requisitos não funcionais

- **Simplicidade:** um empreendedor conclui o fluxo sem ajuda técnica
- **Segurança:** isolamento de dados por usuário, proteção de credenciais, LGPD
- **Desempenho:** respostas do chatbot em tempo aceitável para conversa
- **Extensibilidade:** trocar/adicionar provedores de IA sem reestruturar a aplicação
- **Transparência:** limites e custos visíveis ao usuário

## 7. Critérios de sucesso do MVP

- Usuário novo cria e publica um chatbot funcional sem suporte
- Chatbot responde com base nos documentos enviados
- Widget funciona em um site externo com um único snippet
- Dados de um usuário nunca são acessíveis por outro

## 8. Riscos iniciais

| Risco | Mitigação prevista |
|---|---|
| Custo de uso dos modelos de IA | Limites de mensagens, camada de provedores, cache |
| Respostas incorretas ("alucinação") | RAG, ambiente de testes, instruções restritivas |
| Abuso do widget público | Rate limit, validação de origem, limites por bot |
| Vazamento de dados entre usuários | Isolamento por tenant, testes automatizados |

## 9. Pontos em aberto (a aprofundar)

- Provedor(es) de IA inicial(is) e estratégia de custos
- Modelo de embeddings e estratégia de chunking
- Hospedagem e infraestrutura
- Identidade visual definitiva
- Definição de limites e preços dos planos
- Estratégia de validação com os primeiros usuários
