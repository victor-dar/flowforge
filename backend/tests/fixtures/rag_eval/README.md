# Corpus fictício de avaliação de conhecimento

Este conjunto é um fixture versionado para construir e comparar a recuperação de contexto do FlowForge. Os arquivos não representam clientes reais.

- `manual_atendimento.txt`, `politica_comercial.md` e `faq_tecnico.csv` são as fontes.
- `questions.json` contém 11 perguntas com chatbot de escopo, documentos esperados, trechos de referência, categoria e comportamento esperado.
- Casos `no_answer` devem levar o assistente a se abster.
- Casos `chatbot_isolation` indicam fontes que existem em outro chatbot e não podem aparecer no contexto recuperado.
- Casos `multi_document` exigem evidência das duas fontes indicadas.

Os testes atuais validam a estrutura do corpus e a correspondência dos trechos de referência com as fontes. Eles **não** medem ainda recall, ranking ou qualidade de respostas: essa avaliação só será executável quando o pipeline de recuperação e geração for implementado.
