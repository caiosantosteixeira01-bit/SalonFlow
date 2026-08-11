# SalonFlow

SalonFlow e um sistema desktop para gestao de salao de beleza, construido em Python com interface grafica em `PySide6` e persistencia local em `SQLite`.

O projeto foi pensado para uso local, com foco em operacao diaria, agenda de atendimentos, cadastro de clientes, controle financeiro e geracao de recibos em PDF.

## Status do projeto

Status atual: `ativo e funcional em ambiente local`

O sistema ja possui:

- agenda com fluxo de atendimento
- cadastro de clientes, servicos e profissionais
- financeiro integrado
- caixa
- comissoes
- recibos em PDF
- backup local
- auditoria
- controle de acesso por perfis
- testes automatizados
- empacotamento para Windows com `PyInstaller` e `Inno Setup`

O projeto ainda usa banco local em arquivo e e mais adequado para operacao local do que para uso multiusuario remoto.

## Principais funcionalidades

- Dashboard com indicadores operacionais
- Agenda de atendimentos com status e controle de fluxo
- Cadastro de clientes com historico e ficha
- Cadastro de servicos
- Cadastro de profissionais
- Controle financeiro com recebimentos e pagamentos
- Controle de caixa
- Controle de comissoes
- Geracao e reimpressao de recibos em PDF
- Backup e restauracao do banco
- Auditoria de acoes
- Permissoes por perfil de usuario
- Confirmacao por WhatsApp usando navegador padrao

## Tecnologias utilizadas

- Python 3.13
- PySide6
- SQLite
- ReportLab
- pypdf
- pytest
- PyInstaller
- Inno Setup

## Como instalar

### Ambiente de desenvolvimento

No Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Se for gerar executavel:

```powershell
pip install -r requirements-build.txt
```

## Como executar

No ambiente de desenvolvimento:

```powershell
python main.py
```

Ou com caminho completo do Python:

```powershell
C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\python.exe main.py
```

## Como rodar os testes

Na raiz de `workspace/salao`:

```powershell
python -m pytest tests -q
```

Ou:

```powershell
C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests -q
```

## Estrutura de pastas

```text
workspace/salao/
├── main.py
├── README.md
├── requirements.txt
├── requirements-build.txt
├── build.bat
├── SalonFlow.spec
├── SalonFlow.iss
├── salao/
│   ├── app.py
│   ├── auth.py
│   ├── cli.py
│   ├── client_profile.py
│   ├── database.py
│   ├── finance.py
│   ├── models.py
│   ├── receipt.py
│   ├── salon.py
│   ├── ui.py
│   ├── utils.py
│   ├── whatsapp.py
│   ├── assets/
│   ├── core/
│   └── desktop/
├── tests/
├── documents/
├── backups/
├── logs/
├── build/
├── dist/
└── installer/
```

## Modulos principais

### `salao/app.py`

Ponto de inicializacao da aplicacao `SalonFlow`.

### `salao/database.py`

Cria e acessa o banco SQLite local, incluindo a inicializacao do schema.

### `salao/salon.py`

Camada principal das regras de negocio de agenda, clientes, servicos e profissionais.

### `salao/finance.py`

Centraliza contas a receber, contas a pagar, pagamentos, comissoes, caixa, backup e restauracao.

### `salao/receipt.py`

Gera recibos PDF com base nos dados reais do sistema.

### `salao/auth.py`

Autenticacao, perfis de acesso e auditoria.

### `salao/client_profile.py`

Trata detalhes e historico da ficha da cliente.

### `salao/desktop/main_window.py`

Contem a interface desktop principal do sistema.

## Agenda

A agenda e um dos modulos centrais do `SalonFlow`.

Recursos atuais:

- criacao de agendamentos
- edicao de agendamentos
- cancelamento
- conclusao de atendimento
- marcacao de confirmacao
- integracao com confirmacao por WhatsApp
- filtros por contexto operacional
- atualizacao do dashboard conforme o estado dos atendimentos

## Clientes

O cadastro de clientes permite manter dados operacionais do salao e apoiar o atendimento.

Recursos atuais:

- cadastro e edicao
- ficha da cliente
- observacoes
- historico relacionado ao atendimento
- integracao com agenda e financeiro

## Servicos

O modulo de servicos organiza o catalogo utilizado nos atendimentos.

Recursos atuais:

- nome
- categoria
- duracao
- preco
- ativacao e uso no agendamento

## Profissionais

O modulo de profissionais sustenta a agenda e as comissoes.

Recursos atuais:

- cadastro
- especialidade
- telefone
- status ativo
- vinculacao com atendimentos e comissoes

## Financeiro

O modulo financeiro e integrado ao fluxo operacional do salao.

Recursos atuais:

- contas a receber
- contas a pagar
- recebimentos
- pagamentos
- resumo financeiro
- cobrancas internas
- vinculacao com atendimentos

## Comissoes

As comissoes sao geradas a partir dos atendimentos e do fluxo financeiro.

Recursos atuais:

- calculo de comissao
- listagem
- pagamento de comissoes
- rastreabilidade via auditoria

## Caixa

O controle de caixa acompanha a movimentacao operacional.

Recursos atuais:

- abertura de caixa
- fechamento de caixa
- entradas
- saidas
- saldo esperado
- diferenca no fechamento

## Recibos em PDF

O sistema gera recibos em PDF usando dados reais dos pagamentos registrados.

Recursos atuais:

- geracao
- reimpressao
- salvar como PDF
- abertura do recibo gerado

## Backup

O `SalonFlow` possui rotinas de backup local do banco SQLite.

Recursos atuais:

- criacao de backup
- validacao de integridade do arquivo
- restauracao com copia de seguranca antes da troca

## Auditoria

O sistema registra eventos relevantes para rastreabilidade operacional.

Exemplos:

- login
- logout
- criacao e edicao de entidades
- backup
- pagamentos
- confirmacoes

## Permissoes de usuarios

O acesso e controlado por perfis.

O projeto possui restricoes de acesso para acoes como:

- gerenciar agenda
- gerenciar clientes
- acessar financeiro
- gerar backups
- visualizar ou alterar configuracoes

## Observacoes importantes sobre banco de dados local

Em modo de desenvolvimento, o banco padrao fica em:

`salao/salon.db`

Isso significa:

- o banco e local
- ele nao deve ser publicado no GitHub
- ele nao deve ser usado como artefato de distribuicao
- dados reais devem permanecer fora do repositrio

Na versao empacotada para Windows, o projeto foi preparado para usar `%LOCALAPPDATA%\SalonFlow\` como area de dados persistentes.

## Empacotamento Windows

O repositrio inclui suporte de build para distribuicao Windows:

- `build.bat`
- `SalonFlow.spec`
- `SalonFlow.iss`

Saidas esperadas:

- executavel em `dist/SalonFlow/SalonFlow.exe`
- instalador em `installer/output/SalonFlow-Setup-1.0.0.exe`

Esses artefatos de build nao devem ser commitados no repositrio.

## Observacoes importantes

- nao versionar bancos locais
- nao versionar backups
- nao versionar recibos reais
- nao versionar logs
- nao versionar arquivos `.env` ou credenciais

## Licenca

Este projeto esta licenciado sob a licenca MIT. Veja [LICENSE](./LICENSE).
