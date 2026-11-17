# Contribuindo

Obrigado por ajudar no FlowForge. O projeto é um MVP em desenvolvimento; abra uma issue para discutir mudanças amplas antes de investir em uma implementação.

## Fluxo de contribuição

1. Faça fork e crie uma branch curta, por exemplo `feat/widget-origins` ou `fix/document-upload`.
2. Mantenha cada mudança focada e explique a motivação no pull request.
3. Atualize a documentação diretamente relacionada.
4. Execute os testes e validações aplicáveis.
5. Abra um pull request com resumo, passos de teste, capturas para mudanças visuais e observações de migração/configuração.

## Ambiente e validações

Backend:

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

## Diretrizes

- Documentação e interface voltadas ao usuário devem usar português brasileiro.
- Backend: Python tipado, FastAPI, SQLAlchemy e Pytest.
- Frontend: TypeScript e React; preserve os padrões existentes e prefira componentes reutilizáveis.
- Não inclua `.env`, chaves, dados locais, banco SQLite ou credenciais em commits.
- Mudanças de API/configuração devem atualizar os guias e exemplos.
- Evite declarar recurso pronto antes de sua implementação e validação.
