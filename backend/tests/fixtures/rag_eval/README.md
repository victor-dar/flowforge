# Corpus fictício de avaliação de conhecimento

Este conjunto é um fixture versionado para construir e comparar a recuperação de contexto do FlowForge. Os arquivos não representam clientes reais.

- `manual_atendimento.txt`, `politica_comercial.md` e `faq_tecnico.csv` são as fontes.
- `questions.json` contém 11 perguntas com chatbot de escopo, documentos esperados, trechos de referência, categoria e comportamento esperado.
- Casos `no_answer` devem levar o assistente a se abster.
- Casos `chatbot_isolation` indicam fontes que existem em outro chatbot e não podem aparecer no contexto recuperado.
- Casos `multi_document` exigem evidência das duas fontes indicadas.

Os testes validam a estrutura do corpus, a correspondência dos trechos e métricas de recuperação:

- recall das fontes esperadas;
- sucesso das respostas por fonte;
- isolamento entre chatbots;
- MRR (Mean Reciprocal Rank).

Execute o relatório pela raiz do repositório:

```bash
cd backend
python -m app.rag_eval
```
