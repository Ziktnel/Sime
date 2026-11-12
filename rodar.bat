@echo off
REM SIME - sobe backend (porta 8010) e frontend (porta 3000).
REM Pre-requisitos: Python 3.11+ e Node 20+ no PATH.
setlocal
cd /d "%~dp0"
REM Sem Node instalado, usa o Node portatil da pasta do trabalho 3.
where npm >nul 2>nul || for /d %%A in ("%USERPROFILE%\OneDrive\*rea de Trabalho") do for /d %%B in ("%%~fA\Programa*o para Internet trabalho 3") do set "PATH=%%~fB\.runtime\node;%PATH%"
where npm >nul 2>nul || (echo Node.js nao encontrado. Instale em https://nodejs.org & goto :erro)
if not exist backend\.venv (
  echo [1/3] Criando ambiente Python...
  python -m venv backend\.venv || goto :erro
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :erro
)
if not exist frontend\node_modules (
  echo [2/3] Instalando dependencias do frontend...
  pushd frontend && call npm install && popd || goto :erro
)
echo [3/3] Iniciando servicos. Acesse http://localhost:3000  (API: http://localhost:8010/api/docs)
start "SIME API" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8010"
start "SIME Web" cmd /k "cd /d %~dp0frontend && set OHMNIA_BACKEND_URL=http://localhost:8010&& npm run dev"
goto :eof
:erro
echo Falha na preparacao do ambiente.
exit /b 1
