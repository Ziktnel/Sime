from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.db import get_db
from app.core.security import (BLOQUEIO_MINUTOS, MAX_TENTATIVAS, PERFIS, conferir_senha, criar_token, hash_senha,
                               permissoes_do_perfil, usuario_atual, validar_forca_senha)
from app.models import Usuario

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Login(BaseModel):
    matricula: str = Field(min_length=3, max_length=20)
    senha: str = Field(min_length=1, max_length=128)


class TrocaSenha(BaseModel):
    senha_atual: str
    nova_senha: str


def sessao(u: Usuario) -> dict:
    return {"matricula": u.matricula, "nome": u.nome, "email": u.email, "perfil": u.perfil,
            "perfil_nome": PERFIS.get(u.perfil, {}).get("nome", u.perfil), "area": u.area,
            "permissoes": permissoes_do_perfil(u.perfil)}


@router.post("/login")
def login(body: Login, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter_by(matricula=body.matricula.strip().upper()).first()
    agora = datetime.now()
    if u and u.bloqueado_ate and u.bloqueado_ate > agora:
        raise HTTPException(423, f"Usuário bloqueado por tentativas inválidas até {u.bloqueado_ate:%H:%M}.")
    if not u or not conferir_senha(body.senha, u.senha_hash):
        if u:
            u.tentativas_falhas += 1
            if u.tentativas_falhas >= MAX_TENTATIVAS:
                u.bloqueado_ate, u.tentativas_falhas = agora + timedelta(minutes=BLOQUEIO_MINUTOS), 0
            db.commit()
        raise HTTPException(401, "Matrícula ou senha inválidas.")
    if not u.ativo:
        raise HTTPException(403, "Usuário inativo. Procure o administrador.")
    u.tentativas_falhas, u.bloqueado_ate, u.ultimo_login = 0, None, agora
    registrar(db, "usuario", u.id, "login", u.matricula)
    db.commit()
    return {"access_token": criar_token(u), "token_type": "bearer", "user": sessao(u)}


@router.get("/me")
def me(u: Usuario = Depends(usuario_atual)):
    return sessao(u)


@router.put("/senha")
def trocar_senha(body: TrocaSenha, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    if not conferir_senha(body.senha_atual, u.senha_hash):
        raise HTTPException(400, "Senha atual incorreta.")
    if msg := validar_forca_senha(body.nova_senha):
        raise HTTPException(422, msg)
    u.senha_hash = hash_senha(body.nova_senha)
    registrar(db, "usuario", u.id, "troca_senha", u.matricula)
    db.commit()
    return {"ok": True}
