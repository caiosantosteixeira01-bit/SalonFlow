@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

call :find_python
if not defined PYTHON_EXE (
    echo [Build] Python nao encontrado.
    exit /b 1
)

set "VERSION_FILE=%TEMP%\salonflow_version.txt"
if exist "%VERSION_FILE%" del /q "%VERSION_FILE%"

"%PYTHON_EXE%" %PYTHON_ARGS% -c "from salao.core.version import APP_VERSION; print(APP_VERSION)" > "%VERSION_FILE%"
if errorlevel 1 (
    echo [Build] Falha ao ler a versao do SalonFlow.
    exit /b 1
)

set /p APP_VERSION=<"%VERSION_FILE%"
if exist "%VERSION_FILE%" del /q "%VERSION_FILE%"
if not defined APP_VERSION (
    echo [Build] Nao foi possivel ler a versao do SalonFlow.
    exit /b 1
)

echo [Build] Python: %PYTHON_EXE%
echo [Build] Versao: %APP_VERSION%

"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller --noconfirm --clean SalonFlow.spec
if errorlevel 1 exit /b 1

call :build_installer

echo [Build] Executavel pronto em: %cd%\dist\SalonFlow\SalonFlow.exe
if exist "%cd%\installer\output\SalonFlow-Setup-%APP_VERSION%.exe" (
    echo [Build] Instalador pronto em: %cd%\installer\output\SalonFlow-Setup-%APP_VERSION%.exe
)
exit /b 0

:find_python
set "PYTHON_ARGS="
if defined PYTHON_EXE exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if defined PYTHON_EXE exit /b 0
where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3.13"
)
if defined PYTHON_EXE exit /b 0
where python >nul 2>nul
if not errorlevel 1 set "PYTHON_EXE=python"
exit /b 0

:build_installer
set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\JRSoftware\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\JRSoftware\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do (
    set "ISCC_EXE=%%i"
    goto :iscc_found
)
:iscc_found
if not defined ISCC_EXE (
    echo [Build] Inno Setup nao encontrado. Executavel gerado sem instalador.
    echo [Build] Verifique se o arquivo ISCC.exe existe em uma destas pastas:
    echo [Build]   %ProgramFiles(x86)%\Inno Setup 6
    echo [Build]   %ProgramFiles%\Inno Setup 6
    echo [Build]   %LOCALAPPDATA%\Programs\Inno Setup 6
    echo [Build]   %LOCALAPPDATA%\JRSoftware\Inno Setup 6
    exit /b 0
)
echo [Build] Gerando instalador com Inno Setup...
"%ISCC_EXE%" "/DAppVersion=%APP_VERSION%" "SalonFlow.iss"
exit /b %errorlevel%
