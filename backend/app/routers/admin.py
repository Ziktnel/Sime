"""Gerenciamento: usuários, rotinas, notificações, integrações simuladas, auditoria e acessos."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.db import get_db
from app.core.security import PERFIS, autorizado, hash_senha, require_permission, usuario_atual, validar_forca_senha
from app.integrations.simulador import chamar
from app.models import Agendamento, Historico, IntegracaoConfig, JobRun, Notificacao, Registro, Usuario
from app.recursos import RECURSOS
from app.routers.operacao import _run
from app.services import jobs

router = APIRouter(tags=["gerenciamento"])


def _u(u: Usuario) -> dict:
    return {"matricula": u.matricula, "nome": u.nome, "email": u.email, "perfil": u.perfil, "area": u.area, "ativo": u.ativo,
            "vinculo_ativo": u.vinculo_ativo, "ultimo_login": u.ultimo_login.isoformat() if u.ultimo_login else None,
            "bloqueado": bool(u.bloqueado_ate)}


class NovoUsuario(BaseModel):
    matricula: str = Field(pattern=r"^[A-Z]{2}\d{4}$")
    nome: str = Field(min_length=3, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    perfil: str
    area: str = ""
    senha: str


class EditarUsuario(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    perfil: str | None = None
    area: str | None = None
    ativo: bool | None = None
    nova_senha: str | None = None


@router.get("/api/admin/usuarios")
def usuarios(q: str | None = None, _: Usuario = Depends(require_permission("gerenciamento:usuarios:visualizar")), db: Session = Depends(get_db)):
    us = db.query(Usuario).order_by(Usuario.matricula).all()
    if q:
        us = [u for u in us if q.lower() in f"{u.matricula} {u.nome} {u.email}".lower()]
    return {"itens": [_u(u) for u in us], "perfis": {k: v["nome"] for k, v in PERFIS.items()}}


@router.post("/api/admin/usuarios", status_code=201)
def criar_usuario(body: NovoUsuario, user: Usuario = Depends(require_permission("gerenciamento:usuarios:criar")), db: Session = Depends(get_db)):
    if body.perfil not in PERFIS:
        raise HTTPException(422, "Perfil inexistente.")
    if msg := validar_forca_senha(body.senha):
        raise HTTPException(422, msg)
    if db.query(Usuario).filter_by(matricula=body.matricula).first():
        raise HTTPException(409, "Matrícula já cadastrada.")
    u = Usuario(matricula=body.matricula, nome=body.nome, email=body.email, perfil=body.perfil, area=body.area, senha_hash=hash_senha(body.senha))
    db.add(u)
    db.flush()
    registrar(db, "usuario", u.id, "criacao", user.matricula, depois=_u(u))
    db.commit()
    return _u(u)


@router.put("/api/admin/usuarios/{matricula}")
def editar_usuario(matricula: str, body: EditarUsuario, user: Usuario = Depends(require_permission("gerenciamento:usuarios:editar")),
                   db: Session = Depends(get_db)):
    u = db.query(Usuario).filter_by(matricula=matricula).first()
    if not u:
        raise HTTPException(404, "Usuário não encontrado.")
    if body.perfil and body.perfil not in PERFIS:
        raise HTTPException(422, "Perfil inexistente.")
    if u.matricula == user.matricula and (body.ativo is False or (body.perfil and body.perfil != u.perfil)):
        raise HTTPException(409, "Você não pode desativar nem trocar o próprio perfil.")
    antes = _u(u)
    for k in ("nome", "email", "perfil", "area", "ativo"):
        if getattr(body, k) is not None:
            setattr(u, k, getattr(body, k))
    if body.nova_senha:
        if msg := validar_forca_senha(body.nova_senha):
            raise HTTPException(422, msg)
        u.senha_hash, u.bloqueado_ate, u.tentativas_falhas = hash_senha(body.nova_senha), None, 0
    registrar(db, "usuario", u.id, "edicao", user.matricula, antes=antes, depois=_u(u))
    db.commit()
    return _u(u)


@router.get("/api/admin/acessos")
def acessos(_: Usuario = Depends(require_permission("gerenciamento:usuarios:visualizar"))):
    """Matriz perfil × tela (o que cada perfil enxerga)."""
    telas = [(r.titulo, f"{r.permissao}:visualizar") for r in RECURSOS.values()] + [
        ("Painel", "dashboard:visualizar"), ("Visão 360", "visao-360:visualizar"), ("Diagnóstico MT", "gestao-mt:diagnostico:visualizar"),
        ("Laboratório — análises", "analise-medidores:entrada-manual:visualizar"), ("Aprovações", "analise-medidores:aprovar"),
        ("Console de telemetria", "telemetria:visualizar"), ("Usuários", "gerenciamento:usuarios:visualizar")]
    return {"perfis": {k: v["nome"] for k, v in PERFIS.items()},
            "telas": [{"tela": t, "permissao": p, **{k: autorizado(k, p) for k in PERFIS}} for t, p in telas]}


@router.get("/api/admin/auditoria")
def auditoria(entidade: str | None = None, usuario: str | None = None, limite: int = 200,
              _: Usuario = Depends(require_permission("gerenciamento:usuarios:visualizar")), db: Session = Depends(get_db)):
    q = db.query(Historico)
    if entidade:
        q = q.filter_by(entidade=entidade)
    if usuario:
        q = q.filter_by(usuario=usuario.upper())
    return [{"id": h.id, "entidade": h.entidade, "entidade_id": h.entidade_id, "acao": h.acao, "usuario": h.usuario,
             "texto": h.texto, "depois": h.depois, "em": h.em.isoformat()} for h in q.order_by(Historico.id.desc()).limit(min(limite, 1000))]


@router.get("/api/admin/auditoria-vinculos")
def vinculos(_: Usuario = Depends(require_permission("gerenciamento:usuarios:visualizar")), db: Session = Depends(get_db)):
    us = db.query(Usuario).all()
    return {"total": len(us), "ativos": sum(u.ativo for u in us),
            "desligados_com_acesso": [_u(u) for u in us if not u.vinculo_ativo and u.ativo],
            "revogados": [_u(u) for u in us if not u.vinculo_ativo and not u.ativo]}


# ================================================================ Rotinas
@router.get("/api/jobs")
def listar_jobs(_: Usuario = Depends(require_permission("gerenciamento:tarefas:visualizar")), db: Session = Depends(get_db)):
    ags = {a.job_key: a for a in db.query(Agendamento).all()}
    out = []
    for k, j in jobs.JOBS.items():
        ult = db.query(JobRun).filter_by(job_key=k).order_by(JobRun.id.desc()).first()
        ag = ags.get(k)
        out.append({"job_key": k, "titulo": j["titulo"], "area": j["area"],
                    "agendamento": {"horario": ag.horario, "ativo": ag.ativo} if ag else None, "ultima": _run(ult) if ult else None})
    return out


@router.post("/api/jobs/{job_key}/executar", status_code=202)
def executar(job_key: str, parametros: dict | None = None, user: Usuario = Depends(require_permission("gerenciamento:tarefas:executar")),
             db: Session = Depends(get_db)):
    if job_key not in jobs.JOBS:
        raise HTTPException(404, "Rotina inexistente.")
    try:
        run = jobs.disparar(db, job_key, parametros or {}, usuario=user.matricula)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return _run(run)


@router.get("/api/jobs/runs")
def runs(job_key: str | None = None, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    q = db.query(JobRun)
    if job_key:
        q = q.filter_by(job_key=job_key)
    return [_run(r) for r in q.order_by(JobRun.id.desc()).limit(50)]


@router.get("/api/jobs/runs/{run_id}")
def run(run_id: int, _: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    r = db.get(JobRun, run_id)
    if not r:
        raise HTTPException(404, "Execução não encontrada.")
    return {**_run(r), "log": r.log}


@router.post("/api/jobs/runs/{run_id}/cancelar")
def cancelar(run_id: int, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    r = db.get(JobRun, run_id)
    if not r:
        raise HTTPException(404, "Execução não encontrada.")
    if r.status != "running":
        raise HTTPException(409, "A execução não está em andamento.")
    if r.disparado_por != user.matricula and not autorizado(user.perfil, "gerenciamento:tarefas:executar"):
        raise HTTPException(403, "Só quem disparou ou um gestor pode cancelar.")
    r.status = "cancelled"
    db.commit()
    return {"ok": True}


class Agenda(BaseModel):
    horario: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    ativo: bool


@router.put("/api/jobs/{job_key}/agendamento")
def agendar(job_key: str, body: Agenda, user: Usuario = Depends(require_permission("gerenciamento:tarefas:executar")), db: Session = Depends(get_db)):
    ag = db.get(Agendamento, job_key)
    if not ag:
        raise HTTPException(404, "Rotina sem agendamento.")
    ag.horario, ag.ativo = body.horario, body.ativo
    registrar(db, "agendamento", 0, "edicao", user.matricula, depois={"job": job_key, **body.model_dump()})
    db.commit()
    return {"ok": True}


# ============================================================ Notificações
@router.get("/api/notificacoes")
def notificacoes(user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    ns = db.query(Notificacao).filter_by(usuario_id=user.id).order_by(Notificacao.id.desc()).limit(30).all()
    return {"nao_lidas": db.query(Notificacao).filter_by(usuario_id=user.id, lida=False).count(),
            "itens": [{"id": n.id, "titulo": n.titulo, "texto": n.texto, "link": n.link, "lida": n.lida, "em": n.em.isoformat()} for n in ns]}


@router.put("/api/notificacoes/{nid}/lida")
def marcar_lida(nid: int, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    n = db.get(Notificacao, nid)
    if not n or n.usuario_id != user.id:
        raise HTTPException(404, "Notificação não encontrada.")
    n.lida = True
    db.commit()
    return {"ok": True}


@router.put("/api/notificacoes/lidas")
def marcar_todas(user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    db.query(Notificacao).filter_by(usuario_id=user.id, lida=False).update({"lida": True})
    db.commit()
    return {"ok": True}


# ================================================= Integrações simuladas
@router.get("/api/integracoes")
def integracoes(_: Usuario = Depends(require_permission("gerenciamento:integracoes:visualizar")), db: Session = Depends(get_db)):
    return [{"nome": i.nome, "descricao": i.descricao, "modo": i.modo, "latencia_ms": i.latencia_ms, "chamadas": i.chamadas, "falhas": i.falhas}
            for i in db.query(IntegracaoConfig).order_by(IntegracaoConfig.nome)]


class ModoIntegracao(BaseModel):
    modo: str = Field(pattern=r"^(normal|vazio|falha|lento)$")
    latencia_ms: int = Field(default=1500, ge=0, le=5000)


@router.put("/api/integracoes/{nome}")
def configurar_integracao(nome: str, body: ModoIntegracao, user: Usuario = Depends(require_permission("gerenciamento:integracoes:editar")),
                          db: Session = Depends(get_db)):
    i = db.get(IntegracaoConfig, nome)
    if not i:
        raise HTTPException(404, "Integração inexistente.")
    i.modo, i.latencia_ms = body.modo, body.latencia_ms
    registrar(db, "integracao", 0, "modo", user.matricula, depois={"nome": nome, **body.model_dump()})
    db.commit()
    return {"ok": True}


# ======================================================= Sugestões → issue
@router.post("/api/sugestoes/{rid}/encaminhar")
def encaminhar_sugestao(rid: int, user: Usuario = Depends(require_permission("sugestoes:editar")), db: Session = Depends(get_db)):
    """Abre uma issue no issue tracker simulado e grava o número na sugestão."""
    r = db.get(Registro, rid)
    if not r or r.recurso != "sugestoes":
        raise HTTPException(404, "Sugestão não encontrada.")
    if (r.dados or {}).get("issue"):
        raise HTTPException(409, f"Já vinculada à issue {r.dados['issue']}.")
    chamar(db, "issues")
    numeros = [int(m.group(1)) for x in db.query(Registro).filter_by(recurso="sugestoes").all()
               if (m := re.match(r"#(\d+)", str((x.dados or {}).get("issue") or "")))]
    numero = f"#{max(numeros or [100]) + 1}"
    r.dados = {**r.dados, "issue": numero}
    r.versao += 1
    registrar(db, "sugestoes", r.id, "issue", user.matricula, texto=f"Issue {numero} aberta no tracker simulado")
    db.commit()
    return {"issue": numero}
