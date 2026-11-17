# FériasFlow — Gestão Inteligente de Férias

## Sobre o projeto
O FériasFlow é um MVP acadêmico de gestão de férias, desenvolvido em Python, Flask e SQLite, utilizando a empresa fictícia Kitasawa como contexto de demonstração.

## Objetivo
Facilitar o planejamento, a solicitação e a análise de férias dos colaboradores por meio de uma interface simples e organizada.

## Tecnologias utilizadas
- Python — linguagem de programação
- Flask — framework web
- SQLite — banco de dados
- HTML e CSS — estrutura e apresentação das telas

## Funcionalidades
- Autenticação de usuários de demonstração
- Painel inicial com saldo de férias
- Visualização do período aquisitivo e prazo concessivo
- Solicitação de férias com datas de início e término
- Cálculo demonstrativo de dias corridos
- Acompanhamento do status das solicitações
- Análise, aprovação e rejeição de pedidos por usuários autorizados

## Estrutura do projeto
- app.py — aplicação Flask
- templates/ — páginas HTML
- static/ — arquivos de estilo e recursos visuais
- requirements.txt — dependências Python
- LEIA-ME.txt — informações adicionais

## Como executar localmente
1. Instale o Python.
2. Abra o terminal na pasta do projeto.
3. Instale as dependências: `pip install -r requirements.txt`
4. Execute: `python app.py`
5. Acesse: `http://127.0.0.1:5000`

## Segurança e privacidade
O protótipo utiliza contas e dados fictícios. Não publique bancos de dados locais, senhas reais, chaves secretas ou informações pessoais no repositório público.

## Contexto acadêmico


## Revisão técnica do MVP

Esta revisão documenta aspectos técnicos do FériasFlow para orientar a manutenção e a evolução do sistema.

### Segurança
- Verificar a proteção das senhas por hash seguro.
- Revisar o controle de acesso conforme o perfil do usuário.
- Garantir que dados reais e chaves secretas não sejam publicados no GitHub.

### Organização e legibilidade
- Manter as rotas Flask organizadas e com nomes claros.
- Separar as interfaces HTML dos recursos CSS.
- Documentar as principais funcionalidades do sistema.

### Melhorias propostas
- Ampliar os testes automatizados das solicitações de férias.
- Verificar mensagens de erro e validação de datas.
- Revisar a acessibilidade dos formulários e botões.

As melhorias propostas deverão ser verificadas e implementadas conforme a evolução do MVP.
Projeto desenvolvido para a disciplina Projeto de Software, com práticas de prototipação, implementação, versionamento e validação de funcionalidades.

## Observação
O sistema é um protótipo acadêmico. Os cálculos e informações de férias devem ser conferidos pelo setor de Recursos Humanos antes de qualquer utilização real.
