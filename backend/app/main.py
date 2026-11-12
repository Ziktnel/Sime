"""Ohmnia — API. Executar: uvicorn app.main:app --reload (dentro de backend/)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core import db as dbmod
from app.core.config import get_settings
from app.core.db import Base
from app.integrations.simulador import IntegracaoIndisponivel, garantir_integracoes
from app.models import Usuario
from app.routers import admin, analise, auth, operacao, painel, recursos
from app.services import jobs

log = logging.getLogger("ohmnia")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(dbmod.engine)
    db = dbmod.SessionLocal()
    try:
        garantir_integracoes(db)
        jobs.garantir_agendamentos(db)
        if not db.query(Usuario).count():
            from app.seed import popular
            log.warning("Banco vazio: gerando base sintética (pode levar alguns segundos)...")
            popular(db)
    finally:
        db.close()
    parar = jobs.iniciar_agendador() if get_settings().scheduler else None
    yield
    if parar:
        parar.set()


app = FastAPI(title="SIME API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan,
              description="Plataforma operacional acadêmica com dados sintéticos e integrações simuladas.")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(IntegracaoIndisponivel)
async def _integracao(_: Request, exc: IntegracaoIndisponivel):
    return JSONResponse(status_code=502, content={"detail": str(exc), "integracao": exc.nome})


@app.exception_handler(RequestValidationError)
async def _validacao(_: Request, exc: RequestValidationError):
    erros = [f"{'.'.join(str(p) for p in e['loc'][1:]) or 'corpo'}: {e['msg'].removeprefix('Value error, ')}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": erros})


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "ohmnia"}


for r in (auth, recursos, painel, analise, operacao, admin):
    app.include_router(r.router)
