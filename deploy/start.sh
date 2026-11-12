#!/bin/sh
# Sobe a API em segundo plano e o site em primeiro plano (o site encaminha /api/* para a API).
cd /app/backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd /app/frontend && exec node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "${PORT:-10000}"
