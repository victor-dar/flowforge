# Threat model: upload e processamento de documentos

## Entradas não confiáveis

- Nome e conteúdo de arquivos enviados por usuários autenticados.
- PDF, TXT, MD e CSV podem conter texto malicioso, metadados ou instruções de prompt.
- Consultas públicas e `visitor_id` podem ser usados para criar ou continuar conversas.

## Ativos protegidos

- Conteúdo documental e conversas.
- Credenciais, JWT/cookies e segredo de assinatura.
- Memória, CPU e armazenamento do processo da API.
- Disponibilidade e integridade do banco.

## Controles existentes

- Autenticação e propriedade do chatbot nas rotas privadas.
- Allowlist de extensões e limites configuráveis de bytes e caracteres.
- Limite de upload processado antes da persistência.
- PDFs processados pela biblioteca `pypdf` em processo da API.
- Texto vazio ou inválido é rejeitado.
- Rate limits persistidos por IP, chatbot e capability.

## Riscos

| Risco | Impacto | Mitigação atual | Próximo controle |
|---|---|---|---|
| PDF ZIP bomb ou arquivo complexo | CPU/memória alta | Limite de bytes e caracteres | Timeout e sandbox isolada |
| Upload concorrente | Esgotamento de recursos | Limite por chat; sem fila | Filas e workers |
| Prompt injection em documento | Conteúdo usado indevidamente pelo modelo | Contexto separado de instruções | Regras do sistema e auditoria |
| Unicode/binário disfarçado | Extração inconsistente | Decodificação UTF-8 estrita em texto | Inspeção de MIME e arquivo |
| Exclusão parcial | Dados residuais | Cascata de banco | Transações e auditoria |
| Falsificação de domínio | Uso externo não previsto | Capability curta assinada | Assinatura robusta e proxy confiável |

## Limites operacionais

- `MAX_DOCUMENT_BYTES`: tamanho bruto máximo.
- `MAX_DOCUMENT_CHARACTERS`: tamanho do texto normalizado.
- `RETENTION_DAYS`: idade máxima para limpeza de conversas.
- Operadores devem configurar limites menores em ambientes compartilhados.

## Responsáveis por incidentes

1. Desabilitar uploads ou o provedor externo.
2. Preservar logs necessários a investigação.
3. Identificar documentos afetados e conversas relacionadas.
4. Revogar capacidades/tokens quando aplicável.
5. Aplicar correção e revisar limites.
