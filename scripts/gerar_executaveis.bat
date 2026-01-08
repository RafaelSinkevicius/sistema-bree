@echo off
echo ========================================
echo GERADOR DE EXECUTAVEIS - BREE SYSTEM
echo ========================================
echo.

REM Ativa o ambiente virtual
echo [1/4] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Nao foi possivel ativar o ambiente virtual!
    echo Certifique-se de que o venv existe e esta configurado corretamente.
    pause
    exit /b 1
)

REM Verifica se PyInstaller esta instalado
echo [2/4] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
)

REM Limpa builds anteriores (opcional)
echo [3/4] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist\BreeAutomacao.exe del /q dist\BreeAutomacao.exe
if exist dist\BreeSistema.exe del /q dist\BreeSistema.exe

REM Gera executavel da automacao
echo [4/4] Gerando executavel da AUTOMACAO...
pyinstaller automacao.spec
if errorlevel 1 (
    echo ERRO ao gerar executavel da automacao!
    pause
    exit /b 1
)

REM Gera executavel do sistema Bree
echo [5/5] Gerando executavel do SISTEMA BREE...
pyinstaller bree.spec
if errorlevel 1 (
    echo ERRO ao gerar executavel do sistema Bree!
    pause
    exit /b 1
)

echo.
echo ========================================
echo EXECUTAVEIS GERADOS COM SUCESSO!
echo ========================================
echo.
echo Executaveis disponiveis em:
echo   - dist\BreeAutomacao.exe (Automação)
echo   - dist\BreeSistema.exe (Sistema Web)
echo.
echo IMPORTANTE:
echo   1. Copie os executaveis para o PC destino
echo   2. Para a automacao: Execute BreeAutomacao.exe
echo   3. Para o sistema: Execute BreeSistema.exe e acesse http://localhost:5000
echo   4. Certifique-se de que o PostgreSQL esta configurado no PC destino
echo   5. A pasta 'logs' sera criada automaticamente
echo.
pause

