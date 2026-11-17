# Guia do usuário

Este guia acompanha a interface atualmente implementada. Os nomes de botões podem mudar conforme o painel evolui.

## 1. Criar uma conta

1. Abra o painel.
2. Escolha **Cadastre-se**.
3. Informe um e-mail válido e uma senha de pelo menos 8 caracteres.
4. Entre com as mesmas credenciais.

No desenvolvimento local, a API precisa estar ativa em `http://localhost:8000` junto com o frontend em `http://localhost:5173`.

## 2. Criar e configurar um assistente

1. Na visão geral, escolha **Criar assistente**.
2. Informe um nome e confirme.
3. Em **Configuração**, preencha empresa, descrição, instruções e mensagem de boas-vindas; escolha uma cor.
4. Aguarde o indicador de salvamento. As alterações são persistidas pela API.

Instruções claras e informações atuais ajudam o assistente, mas não garantem respostas corretas.

## 3. Adicionar documentos

1. Abra **Base de conhecimento**.
2. Selecione PDF, TXT, MD ou CSV de até 5 MB.
3. Aguarde a confirmação. O texto extraído é usado pela busca lexical.

PDFs digitalizados sem camada de texto podem não produzir conteúdo utilizável. Evite enviar informações pessoais ou confidenciais sem revisar as políticas do seu ambiente.

## 4. Testar

1. Abra **Testar assistente**.
2. Envie perguntas que representem situações reais.
3. Teste perguntas sem resposta na base para avaliar como o assistente lida com falta de informação.
4. Use **Limpar conversa** para iniciar outra conversa de teste.

Sem `OPENAI_API_KEY`, o chat retorna trechos encontrados ou informa que não há informação suficiente. Com chave, o backend consulta o modelo configurado.

## 5. Publicar

1. Abra **Publicar** e copie o snippet exibido.
2. Substitua o host da API pela URL HTTPS pública do seu ambiente, caso necessário.
3. Adicione o script ao HTML do site.
4. Teste o widget em uma página de homologação antes de publicar amplamente.

O modo atual não restringe o widget a domínios específicos por chatbot. Considere isso antes de compartilhar o snippet em produção.

## 6. Excluir

Use **Excluir** no assistente e confirme. O backend exclui o chatbot e os dados associados por cascata. Exclusão de conta e exportação de dados ainda não estão disponíveis no painel.

## Problemas comuns

| Sintoma | Verificação |
|---|---|
| Cadastro não responde | Confirme que API e painel estão ativos; veja a aba Network/console do navegador |
| Erro de CORS | Confira `CORS_ORIGINS` e a origem exata do painel |
| Chat indisponível | Confira conectividade/configuração do provedor e limites de requisição |
| Documento rejeitado | Verifique formato, limite de 5 MB e se há texto extraível |
