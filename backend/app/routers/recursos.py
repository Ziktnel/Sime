"""API genérica dos recursos operacionais (ver app/recursos.py)."""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auditoria import diff, registrar
from app.core.db import get_db
from app.core.security import autorizado, usuario_atual
from app.models import Historico, Registro, Usuario
from app.recursos import RECURSOS, Recurso, validar
from app.services import jobs

router = APIRouter(prefix="/api/recursos", tags=["recursos"])


def _rec(chave: str, user: Usuario, acao: str) -> Recurso:
    rec = RECURSOS.get(chave)
    if not rec:
        raise HTTPException(404, "Recurso inexistente.")
    if not autorizado(user.perfil, f"{rec.permissao}:{acao}"):
        raise HTTPException(403, f"Sem permissão: {rec.permissao}:{acao}")
    if acao in ("criar", "editar", "excluir") and rec.somente_leitura:
        raise HTTPException(405, "Recurso somente leitura (alimentado por rotina/integração).")
    return rec


def _linha(r: Registro) -> dict:
    return {"id": r.id, "versao": r.versao, "criado_em": r.criado_em.isoformat(), "atualizado_em": r.atualizado_em.isoformat(),
            "criado_por": r.criado_por, **(r.dados or {})}


def _filtrar(rec: Recurso, regs: list[Registro], q: str | None, filtros: dict[str, str]) -> list[Registro]:
    termo = (q or "").strip().lower()
    out = []
    for r in regs:
        d = r.dados or {}
        if termo and not any(termo in str(v).lower() for v in d.values() if v is not None):
            continue
        if any(str(d.get(k)) != v for k, v in filtros.items()):
            continue
        out.append(r)
    return out


def _ordenar(regs: list[Registro], campo: str | None, direcao: str) -> list[Registro]:
    if not campo:
        return sorted(regs, key=lambda r: r.id, reverse=True)

    def chave(r: Registro):
        v = r.id if campo == "id" else (r.dados or {}).get(campo)
        return (v is None, v if isinstance(v, (int, float)) else str(v or "").lower())
    return sorted(regs, key=chave, reverse=direcao == "desc")


@router.get("")
def listar_recursos(user: Usuario = Depends(usuario_atual)):
    return [{**r.meta(), "acoes": {a: autorizado(user.perfil, f"{r.permissao}:{a}") and not (r.somente_leitura and a in ("criar", "editar", "excluir"))
                                   for a in ("visualizar", "criar", "editar", "excluir", "exportar")}}
            for r in RECURSOS.values() if autorizado(user.perfil, f"{r.permissao}:visualizar")]


@router.get("/{chave}")
def listar(chave: str, request: Request, q: str | None = None, ordenar: str | None = None, direcao: str = "asc",
           pagina: int = Query(1, ge=1), tamanho: int = Query(25, ge=1, le=500),
           user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "visualizar")
    filtros = {k[2:]: v for k, v in request.query_params.items() if k.startswith("f_") and v != ""}
    regs = _ordenar(_filtrar(rec, db.query(Registro).filter_by(recurso=chave).all(), q, filtros), ordenar, direcao)
    contagem: dict[str, dict[str, int]] = {}
    for c in rec.campos:
        if c.filtro:
            cont: dict[str, int] = {}
            for r in regs:
                v = (r.dados or {}).get(c.nome)
                cont[str(v)] = cont.get(str(v), 0) + 1
            contagem[c.nome] = cont
    ini = (pagina - 1) * tamanho
    return {"total": len(regs), "pagina": pagina, "tamanho": tamanho, "itens": [_linha(r) for r in regs[ini:ini + tamanho]],
            "contagem": contagem}


@router.get("/{chave}/export")
def exportar(chave: str, request: Request, q: str | None = None, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "exportar")
    filtros = {k[2:]: v for k, v in request.query_params.items() if k.startswith("f_") and v != ""}
    regs = _ordenar(_filtrar(rec, db.query(Registro).filter_by(recurso=chave).all(), q, filtros), None, "asc")
    buf = io.StringIO()
    buf.write("﻿")  # BOM para o Excel abrir com acentos
    w = csv.writer(buf, delimiter=";")
    w.writerow(["id"] + [c.rotulo for c in rec.campos])
    for r in regs:
        w.writerow([r.id] + [("" if (r.dados or {}).get(c.nome) is None else r.dados[c.nome]) for c in rec.campos])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{chave}.csv"'})


def _checar_unico(db: Session, rec: Recurso, dados: dict, ignorar_id: int | None = None) -> None:
    if not rec.unico or dados.get(rec.unico) in (None, ""):
        return
    for r in db.query(Registro).filter_by(recurso=rec.chave).all():
        if r.id != ignorar_id and (r.dados or {}).get(rec.unico) == dados[rec.unico]:
            raise HTTPException(409, f"Já existe registro com {rec.campo(rec.unico).rotulo} = {dados[rec.unico]}.")


@router.post("/{chave}", status_code=201)
def criar(chave: str, body: dict[str, Any], user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "criar")
    dados, erros = validar(db, rec, body)
    if erros:
        raise HTTPException(422, erros)
    _checar_unico(db, rec, dados)
    r = Registro(recurso=chave, dados=dados, criado_por=user.matricula)
    db.add(r)
    db.flush()
    if rec.efeito:
        rec.efeito(db, dados, None, user.matricula)
    registrar(db, chave, r.id, "criacao", user.matricula, depois=dados)
    db.commit()
    return _linha(r)


@router.get("/{chave}/{rid}")
def obter(chave: str, rid: int, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _rec(chave, user, "visualizar")
    r = db.get(Registro, rid)
    if not r or r.recurso != chave:
        raise HTTPException(404, "Registro não encontrado.")
    return _linha(r)


def _atualizar(db: Session, rec: Recurso, r: Registro, novos: dict, usuario: str) -> dict:
    antes = dict(r.dados or {})
    dados, erros = validar(db, rec, novos, antes)
    if erros:
        raise HTTPException(422, erros)
    _checar_unico(db, rec, dados, r.id)
    a, d = diff(antes, dados)
    if not d:
        return _linha(r)
    r.dados, r.versao = dados, r.versao + 1
    if rec.efeito:
        rec.efeito(db, dados, antes, usuario)
    registrar(db, rec.chave, r.id, "edicao", usuario, antes=a, depois=d)
    return _linha(r)


@router.put("/{chave}/{rid}")
def editar(chave: str, rid: int, body: dict[str, Any], user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "editar")
    r = db.get(Registro, rid)
    if not r or r.recurso != chave:
        raise HTTPException(404, "Registro não encontrado.")
    versao = body.pop("versao", None)
    if versao is not None and int(versao) != r.versao:
        raise HTTPException(409, "O registro foi alterado por outra pessoa. Recarregue antes de salvar.")
    for k in ("id", "criado_em", "atualizado_em", "criado_por"):
        body.pop(k, None)
    out = _atualizar(db, rec, r, body, user.matricula)
    db.commit()
    return out


class StatusMassa(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    status: str


@router.patch("/{chave}/status-em-massa")
def status_em_massa(chave: str, body: StatusMassa, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "editar")
    if not rec.campo_status:
        raise HTTPException(400, "Recurso sem campo de status.")
    ok, falhas = 0, []
    for rid in body.ids:
        r = db.get(Registro, rid)
        if not r or r.recurso != chave:
            falhas.append({"id": rid, "erro": "não encontrado"})
            continue
        try:
            _atualizar(db, rec, r, {rec.campo_status: body.status}, user.matricula)
            ok += 1
        except HTTPException as e:
            falhas.append({"id": rid, "erro": "; ".join(e.detail) if isinstance(e.detail, list) else e.detail})
    db.commit()
    return {"atualizados": ok, "falhas": falhas}


@router.delete("/{chave}/{rid}")
def excluir(chave: str, rid: int, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _rec(chave, user, "excluir")
    r = db.get(Registro, rid)
    if not r or r.recurso != chave:
        raise HTTPException(404, "Registro não encontrado.")
    registrar(db, chave, r.id, "exclusao", user.matricula, antes=r.dados)
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.get("/{chave}/{rid}/historico")
def historico(chave: str, rid: int, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _rec(chave, user, "visualizar")
    hs = db.query(Historico).filter_by(entidade=chave, entidade_id=rid).order_by(Historico.id.desc()).all()
    return [{"id": h.id, "acao": h.acao, "antes": h.antes, "depois": h.depois, "texto": h.texto, "usuario": h.usuario,
             "em": h.em.isoformat()} for h in hs]


class Comentario(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


@router.post("/{chave}/{rid}/comentarios", status_code=201)
def comentar(chave: str, rid: int, body: Comentario, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _rec(chave, user, "visualizar")
    if not db.get(Registro, rid):
        raise HTTPException(404, "Registro não encontrado.")
    registrar(db, chave, rid, "comentario", user.matricula, texto=body.texto.strip())
    db.commit()
    return {"ok": True}


class Importacao(BaseModel):
    csv: str = Field(min_length=1, max_length=2_000_000)


@router.post("/{chave}/importar")
def importar(chave: str, body: Importacao, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Importa CSV (separador ; ou ,) cujo cabeçalho usa nomes ou rótulos dos campos. Valida linha a linha."""
    rec = _rec(chave, user, "criar")
    texto = body.csv.lstrip("﻿")
    sep = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=sep)
    por_rotulo = {c.rotulo.lower(): c.nome for c in rec.campos} | {c.nome.lower(): c.nome for c in rec.campos}
    criados, erros = 0, []
    for n, linha in enumerate(leitor, start=2):
        dados = {por_rotulo[k.strip().lower()]: v for k, v in linha.items() if k and k.strip().lower() in por_rotulo}
        limpo, errs = validar(db, rec, dados)
        if not errs:
            try:
                _checar_unico(db, rec, limpo)
            except HTTPException as e:
                errs = [e.detail]
        if errs:
            erros.append({"linha": n, "erros": errs})
            continue
        r = Registro(recurso=chave, dados=limpo, criado_por=user.matricula)
        db.add(r)
        db.flush()
        registrar(db, chave, r.id, "importacao", user.matricula, depois=limpo)
        criados += 1
    db.commit()
    return {"criados": criados, "erros": erros}


@router.post("/{chave}/atualizar")
def atualizar_base(chave: str, user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    rec = _rec(chave, user, "visualizar")
    if not rec.acao_atualizar:
        raise HTTPException(400, "Recurso sem rotina de atualização.")
    try:
        run = jobs.disparar(db, rec.acao_atualizar, usuario=user.matricula)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"run_id": run.id}
