# SalonFlow 1.0.0

Sistema desktop para salao de beleza com `PySide6`, `SQLite`, financeiro integrado, recibos em PDF e distribuicao Windows preparada para uso comercial.

## Ponto de entrada

- Desenvolvimento: `workspace/salao/main.py`
- Aplicacao Python: `salao.app.run()`
- Interface desktop: `salao.desktop.main_window.run_desktop_app()`

## Dependencias Python

- `PySide6`
- `reportlab`
- `pypdf`
- `pytest`
- Build Windows: `PyInstaller` em `requirements-build.txt`

## Estrutura importante

- Codigo-fonte: `workspace/salao/salao/`
- Assets visuais: `workspace/salao/salao/assets/`
- Testes: `workspace/salao/tests/`
- Spec do PyInstaller: `workspace/salao/SalonFlow.spec`
- Script de build: `workspace/salao/build.bat`
- Instalador Inno Setup: `workspace/salao/SalonFlow.iss`

## Execucao em desenvolvimento

```powershell
python workspace\salao\main.py
```

Ou:

```powershell
C:\Users\caios\AppData\Local\Programs\Python\Python313\python.exe workspace\salao\main.py
```

## Testes

```powershell
python -m pytest workspace\salao\tests -q
```

## Banco e dados do cliente

### Modo desenvolvimento

- Banco: `workspace/salao/salao/salon.db`
- Recibos: `workspace/salao/documents/receipts/`
- Backups: `workspace/salao/backups/`

### Modo empacotado

- Banco: `%LOCALAPPDATA%\SalonFlow\salon.db`
- Recibos: `%LOCALAPPDATA%\SalonFlow\documents\receipts\`
- Backups: `%LOCALAPPDATA%\SalonFlow\backups\`
- Logs de suporte: `%LOCALAPPDATA%\SalonFlow\logs\`

O executavel nao grava dados do cliente em `Program Files`.

## Empacotamento Windows

Foi escolhido `PyInstaller` em modo `one-folder`.

Motivo:

- mais confiavel para `PySide6`
- mais previsivel com `reportlab`
- evita problemas de recursos temporarios
- facilita suporte, backup e diagnostico

### Gerar build

Abra um terminal em `workspace/salao` e rode:

```powershell
.\build.bat
```

O script:

- localiza o Python
- instala dependencias de build
- gera `dist/SalonFlow/SalonFlow.exe`
- tenta gerar o instalador se o Inno Setup estiver instalado

## Saida esperada do build

- Executavel: `workspace/salao/dist/SalonFlow/SalonFlow.exe`
- Instalador: `workspace/salao/installer/output/SalonFlow-Setup-1.0.0.exe`

## Instalador

O arquivo `SalonFlow.iss` prepara:

- instalacao no Windows
- atalho no Menu Iniciar
- opcao de atalho na Area de Trabalho
- desinstalacao normal pelo Windows

O desinstalador nao remove automaticamente `%LOCALAPPDATA%\SalonFlow`, preservando banco, backups e configuracoes.

## Arquivos que devem acompanhar a aplicacao

- modulos Python empacotados
- assets de `salao/assets`
- dependencias do `reportlab`
- dependencias do `pypdf`

Nao devem acompanhar a distribuicao:

- `salon.db` de desenvolvimento
- backups reais
- recibos reais
- caches
- `__pycache__`

## Versionamento

A versao central fica em:

- `workspace/salao/salao/core/version.py`

Altere `APP_VERSION` para futuras distribuicoes como `1.0.1` ou `1.1.0`.

## Checklist de instalacao limpa

1. Instalar o `SalonFlow`.
2. Abrir pelo atalho do Windows.
3. Confirmar criacao de `%LOCALAPPDATA%\SalonFlow`.
4. Fazer login inicial.
5. Cadastrar uma cliente.
6. Cadastrar um profissional.
7. Cadastrar um servico.
8. Criar um agendamento.
9. Confirmar o agendamento.
10. Concluir atendimento.
11. Registrar pagamento.
12. Gerar recibo em PDF.
13. Fechar o aplicativo.
14. Abrir novamente.
15. Confirmar persistencia dos dados.
16. Criar backup.
17. Validar restauracao com seguranca.

## Observacoes de distribuicao

- O build atual nao embute banco real nem recibos reais.
- A geracao de PDF continua fora da pasta do programa.
- A abertura do WhatsApp continua usando o navegador padrao do Windows.
