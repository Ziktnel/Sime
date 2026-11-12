@echo off
REM Ohmnia - sobe backend (porta 8000) e frontend (porta 3000).
REM Pre-requisitos: Python 3.11+ e Node 20+ no PATH.
setlocal
cd /d "%~dp0"
if not exist backend\.venv (
  echo [1/3] Criando ambiente Python...
  python -m venv backend\.venv || goto :erro
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :erro
)
if not exist frontend\node_modules (
  echo [2/3] Instalando dependencias do frontend...
  pushd frontend && call npm install && popd || goto :erro
)
echo [3/3] Iniciando servicos. Acesse http://localhost:3000  (API: http://localhost:8000/api/docs)
start "Ohmnia API" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
start "Ohmnia Web" cmd /k "cd /d %~dp0frontend && npm run dev"
goto :eof
:erro
echo Falha na preparacao do ambiente.
exit /b 1
