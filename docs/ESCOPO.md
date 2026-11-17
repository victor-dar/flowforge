# Escopo e estado do produto

## Visão

FlowForge é uma plataforma no-code em estágio de MVP para pequenos negócios configurarem assistentes de atendimento com informações próprias e publicá-los em sites.

## Público pretendido

Pequenos negócios e profissionais autônomos que precisam responder dúvidas frequentes. O público é uma hipótese de produto; validação com usuários e métricas ainda precisa ser feita.

## Estado funcional

| Funcionalidade | Estado | Observações |
|---|---|---|
| Cadastro e login | Implementado | JWT; sem confirmação de e-mail ou recuperação de senha |
| Dashboard | Implementado | Visão de assistentes e documentos; métricas de conversas ainda não são apresentadas |
| Criar/editar/excluir chatbot | Implementado | Escopo por usuário |
| Configurar aparência e instruções | Implementado | Nome, empresa, descrição, instruções, boas-vindas e cor |
| Upload da base de conhecimento | Implementado | PDF, TXT, MD e CSV; extração simples |
| Busca de contexto | Implementação inicial | Busca lexical; não é RAG vetorial |
| Integração LLM | Implementação inicial | Provedor compatível com API OpenAI, opcional |
| Teste de conversa | Implementado | Interface no painel |
| Widget externo | Implementado | Snippet JavaScript + iframe |
| Histórico | API implementada | Até 100 conversas por chamada; visualização ainda não integrada ao painel |
| Limites de uso | Implementado | Janelas fixas persistidas no banco; não são medição de custo |
| Cobrança e planos | Não implementado | |
| Recuperação de senha e administração | Não implementado | |
| Busca semântica/RAG vetorial | Não implementado | |

## Critérios de validação do MVP

- Uma pessoa consegue criar conta, configurar um assistente e testar o fluxo sem assistência.
- O assistente usa trechos de documentos relevantes em suas respostas.
- O widget pode ser instalado por snippet em uma página externa.
- Dados privados de um usuário não são retornados a outro usuário.

Os critérios devem ser validados com testes e usuários reais antes de afirmar prontidão comercial.

## Fora do escopo atual

WhatsApp, CRM, agendamento, webhooks, editor visual de fluxos, equipes/agências, planos pagos e handoff para agentes humanos.

## Riscos e hipóteses

- Qualidade da busca lexical pode ser baixa em perguntas com vocabulário diferente do documento.
- Conteúdo de usuários finais e documentos pode ser sensível; retenção, exclusão e aviso de privacidade precisam ser definidos.
- Uma cota por mensagens não equivale a uma cota financeira de provedor.
- O widget público necessita controles de origem e abuso adequados para publicação ampla.
