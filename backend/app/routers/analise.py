"""Laboratório de Medidores: entrada, análise, aprovação, laudo, quarentena, indicadores e importação de bancada."""
from __future__ import annotations

import csv
import html
import io
from collections import Counter, defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auditoria import notificar_permissao, registrar
from app.core.db import get_db
from app.core.security import require_permission
from app.models import Analise, Instalacao, Medidor, Usuario

router = APIRouter(prefix="/api/analise-medidores", tags=["analise-medidores"])
P = "analise-medidores"
LIMITE_ERRO = 2.0  # % — acima disso a aferição reprova por exatidão
FLUXO = {"AGUARDANDO": ["EM_ANALISE"], "EM_ANALISE": ["AGUARDANDO_APROVACAO"], "REABERTA": ["AGUARDANDO_APROVACAO"],
         "AGUARDANDO_APROVACAO": ["APROVADA", "REABERTA"], "APROVADA": []}


def _dict(a: Analise) -> dict:
    m = a.medidor
    return {"id": a.id, "protocolo": a.protocolo, "status": a.status, "solicitante": a.solicitante, "nota_servico": a.nota_servico,
            "instalacao": a.instalacao_codigo, "medidor": m.serie, "fabricante": m.fabricante, "modelo": m.modelo,
            "dt_entrada": a.dt_entrada.isoformat(), "dt_agendada": a.dt_agendada.isoformat() if a.dt_agendada else None,
            "dt_analise": a.dt_analise.isoformat() if a.dt_analise else None, "examinador": a.examinador, "aprovador": a.aprovador,
            "resultado": a.resultado, "irregularidade": a.irregularidade, "erro_percentual": a.erro_percentual,
            "lacre_numero": a.lacre_numero, "lacre_integro": a.lacre_integro, "observacao": a.observacao,
            "numero_laudo": a.numero_laudo, "quarentena": a.quarentena, "versao": a.versao}


def _get(db: Session, aid: int) -> Analise:
    a = db.get(Analise, aid)
    if not a:
        raise HTTPException(404, "Análise não encontrada.")
    return a


def _transicao(a: Analise, para: str) -> None:
    if para not in FLUXO.get(a.status, []):
        raise HTTPException(409, f"Não é possível passar de {a.status} para {para}.")
    a.status = para


@router.get("")
def fila(status: str | None = None, q: str | None = None, _: Usuario = Depends(require_permission(f"{P}:entrada-manual:visualizar")),
         db: Session = Depends(get_db)):
    qa = db.query(Analise)
    if status:
        qa = qa.filter_by(status=status)
    itens = [_dict(a) for a in qa.order_by(Analise.dt_entrada.desc()).all()]
    if q:
        t = q.lower()
        itens = [i for i in itens if t in f"{i['protocolo']} {i['medidor']} {i['instalacao']} {i['nota_servico']}".lower()]
    return {"total": len(itens), "itens": itens, "status": dict(Counter(a for (a,) in db.query(Analise.status)))}


class Entrada(BaseModel):
    serie: str = Field(min_length=4, max_length=20)
    solicitante: str
    nota_servico: str | None = Field(default=None, pattern=r"^\d{8,10}$")
    instalacao: str | None = Field(default=None, pattern=r"^\d{10}$")
    dt_agendada: date | None = None

    @field_validator("solicitante")
    @classmethod
    def _sol(cls, v: str) -> str:
        if v not in ("CLIENTE", "DISTRIBUIDORA", "ORGAO_REGULADOR"):
            raise ValueError("solicitante inválido")
        return v


@router.post("", status_code=201)
def entrada(body: Entrada, user: Usuario = Depends(require_permission(f"{P}:entrada-manual:criar")), db: Session = Depends(get_db)):
    m = db.query(Medidor).filter_by(serie=body.serie.strip().upper()).first()
    if not m:
        raise HTTPException(404, f"Medidor {body.serie} não está na base.")
    if db.query(Analise).filter(Analise.medidor_id == m.id, Analise.status != "APROVADA").first():
        raise HTTPException(409, "Já existe análise em aberto para este medidor.")
    if body.instalacao and not db.query(Instalacao.id).filter_by(codigo=body.instalacao).first():
        raise HTTPException(422, "Instalação não encontrada.")
    hoje = date.today()
    seq = (db.query(func.count(Analise.id)).scalar() or 0) + 1
    a = Analise(protocolo=f"AM-{hoje.year}-{seq:05d}", medidor_id=m.id, instalacao_codigo=body.instalacao or (m.instalacao.codigo if m.instalacao else None),
                solicitante=body.solicitante, nota_servico=body.nota_servico, dt_entrada=hoje, dt_agendada=body.dt_agendada, status="AGUARDANDO")
    m.situacao, m.instalacao_id = "LABORATORIO", None
    db.add(a)
    db.flush()
    registrar(db, "analise", a.id, "entrada", user.matricula, depois={"protocolo": a.protocolo, "medidor": m.serie})
    db.commit()
    return _dict(a)


@router.get("/aprovacoes/pendentes")
def pendentes(_: Usuario = Depends(require_permission(f"{P}:aprovar")), db: Session = Depends(get_db)):
    return [_dict(a) for a in db.query(Analise).filter_by(status="AGUARDANDO_APROVACAO").order_by(Analise.dt_analise)]


class Lote(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


@router.post("/aprovacoes/aprovar-lote")
def aprovar_lote(body: Lote, user: Usuario = Depends(require_permission(f"{P}:aprovar")), db: Session = Depends(get_db)):
    ultimo = db.query(Analise.numero_laudo).filter(Analise.numero_laudo.like(f"LAU-{date.today().year}-%")).all()
    seq = max([int(n.split("-")[-1]) for (n,) in ultimo] or [0])
    ok, falhas = [], []
    for aid in body.ids:
        a = db.get(Analise, aid)
        if not a or a.status != "AGUARDANDO_APROVACAO":
            falhas.append({"id": aid, "erro": "não está aguardando aprovação"})
            continue
        if a.examinador == user.nome:
            falhas.append({"id": aid, "erro": "quem examinou não pode aprovar (segregação de função)"})
            continue
        seq += 1
        a.status, a.aprovador, a.numero_laudo = "APROVADA", user.nome, f"LAU-{date.today().year}-{seq:04d}"
        if a.resultado == "IRREGULAR":
            a.quarentena, a.medidor.situacao = "PENDENTE", "QUARENTENA"
        else:
            a.medidor.situacao = "ESTOQUE"
        registrar(db, "analise", a.id, "aprovacao", user.matricula, depois={"laudo": a.numero_laudo})
        ok.append(a.numero_laudo)
    db.commit()
    return {"aprovadas": len(ok), "laudos": ok, "falhas": falhas}


class Reprovar(BaseModel):
    motivo: str = Field(min_length=5, max_length=1000)


@router.post("/{aid}/reabrir")
def reabrir(aid: int, body: Reprovar, user: Usuario = Depends(require_permission(f"{P}:aprovar")), db: Session = Depends(get_db)):
    a = _get(db, aid)
    _transicao(a, "REABERTA")
    registrar(db, "analise", a.id, "reabertura", user.matricula, texto=body.motivo)
    db.commit()
    return _dict(a)


@router.get("/calendario")
def calendario(mes: str | None = None, _: Usuario = Depends(require_permission(f"{P}:calendario:visualizar")), db: Session = Depends(get_db)):
    ref = date.fromisoformat(f"{mes}-01") if mes else date.today().replace(day=1)
    fim = date(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)
    evs = []
    for a in db.query(Analise).filter(Analise.dt_agendada >= ref, Analise.dt_agendada < fim):
        evs.append({"data": a.dt_agendada.isoformat(), "id": a.id, "titulo": f"{a.protocolo} · {a.medidor.serie}", "status": a.status})
    return {"mes": ref.isoformat()[:7], "eventos": evs}


@router.get("/indicadores")
def indicadores(_: Usuario = Depends(require_permission(f"{P}:indicadores:visualizar")), db: Session = Depends(get_db)):
    todas = db.query(Analise).all()
    por_mes: dict[str, Counter] = defaultdict(Counter)
    tempos = []
    for a in todas:
        por_mes[a.dt_entrada.isoformat()[:7]]["entradas"] += 1
        if a.dt_analise:
            por_mes[a.dt_analise.isoformat()[:7]]["analisadas"] += 1
            tempos.append((a.dt_analise - a.dt_entrada).days)
    concl = [a for a in todas if a.resultado]
    por_fab: dict[str, Counter] = defaultdict(Counter)
    for a in concl:
        por_fab[a.medidor.fabricante][a.resultado] += 1
    return {"total": len(todas), "tempo_medio_dias": round(sum(tempos) / len(tempos), 1) if tempos else None,
            "irregularidade_pct": round(100 * sum(a.resultado == "IRREGULAR" for a in concl) / len(concl), 1) if concl else 0,
            "por_mes": [{"mes": k, **v} for k, v in sorted(por_mes.items())][-12:],
            "por_fabricante": [{"fabricante": k, "regular": v["REGULAR"], "irregular": v["IRREGULAR"]} for k, v in sorted(por_fab.items())],
            "irregularidades": [{"tipo": k, "quantidade": v} for k, v in Counter(a.irregularidade for a in concl if a.irregularidade).most_common()]}


@router.get("/quarentena")
def quarentena(_: Usuario = Depends(require_permission(f"{P}:quarentena:visualizar")), db: Session = Depends(get_db)):
    return [_dict(a) for a in db.query(Analise).filter(Analise.quarentena.isnot(None)).order_by(Analise.quarentena.desc(), Analise.id.desc())]


class Vinculo(BaseModel):
    nota_irregularidade: str = Field(pattern=r"^\d{8,10}$")


@router.post("/{aid}/quarentena/vincular")
def vincular(aid: int, body: Vinculo, user: Usuario = Depends(require_permission(f"{P}:quarentena:editar")), db: Session = Depends(get_db)):
    a = _get(db, aid)
    if a.quarentena != "PENDENTE":
        raise HTTPException(409, "Somente medidores com quarentena PENDENTE podem ser vinculados.")
    a.quarentena, a.medidor.situacao = "VINCULADO", "DESCARTADO"
    registrar(db, "analise", a.id, "quarentena_vinculada", user.matricula, texto=f"Nota {body.nota_irregularidade}")
    db.commit()
    return _dict(a)


class Bancada(BaseModel):
    csv: str = Field(min_length=5, max_length=500_000)


@router.post("/sincronizacao-bancada")
def importar_bancada(body: Bancada, user: Usuario = Depends(require_permission(f"{P}:bancada:visualizar")), db: Session = Depends(get_db)):
    """Importa resultado de bancada (serie;erro_percentual;lacre) e preenche as análises em aberto."""
    linhas = list(csv.reader(io.StringIO(body.csv.strip()), delimiter=";"))
    if linhas and len(linhas[0]) > 1 and not any(ch.isdigit() for ch in linhas[0][1]):  # cabeçalho
        linhas = linhas[1:]
    atualizadas, erros = 0, []
    for n, l in enumerate(linhas, 1):
        if len(l) < 2:
            erros.append({"linha": n, "erro": "colunas insuficientes"})
            continue
        m = db.query(Medidor).filter_by(serie=l[0].strip().upper()).first()
        a = db.query(Analise).filter(Analise.medidor_id == m.id, Analise.status.in_(["AGUARDANDO", "EM_ANALISE", "REABERTA"])).first() if m else None
        if not a:
            erros.append({"linha": n, "erro": f"sem análise aberta para {l[0]}"})
            continue
        try:
            a.erro_percentual = float(l[1].replace(",", "."))
        except ValueError:
            erros.append({"linha": n, "erro": "erro percentual inválido"})
            continue
        if len(l) > 2 and l[2].strip():
            a.lacre_numero = l[2].strip()
        if a.status == "AGUARDANDO":
            a.status = "EM_ANALISE"
        a.dt_analise = date.today()
        registrar(db, "analise", a.id, "bancada", user.matricula, depois={"erro_percentual": a.erro_percentual})
        atualizadas += 1
    db.commit()
    return {"atualizadas": atualizadas, "erros": erros}


@router.get("/{aid}")
def obter(aid: int, _: Usuario = Depends(require_permission(f"{P}:entrada-manual:visualizar")), db: Session = Depends(get_db)):
    return _dict(_get(db, aid))


class Salvar(BaseModel):
    versao: int
    resultado: str | None = None
    irregularidade: str | None = None
    erro_percentual: float | None = Field(default=None, ge=-100, le=100)
    lacre_numero: str | None = Field(default=None, max_length=30)
    lacre_integro: bool | None = None
    observacao: str | None = Field(default=None, max_length=4000)


@router.put("/{aid}")
def salvar(aid: int, body: Salvar, user: Usuario = Depends(require_permission(f"{P}:entrada-manual:criar")), db: Session = Depends(get_db)):
    a = _get(db, aid)
    if a.status in ("APROVADA", "AGUARDANDO_APROVACAO"):
        raise HTTPException(409, "Análise bloqueada para edição neste status.")
    if body.versao != a.versao:
        raise HTTPException(409, "A análise foi alterada por outra pessoa. Recarregue.")
    dados = body.model_dump(exclude={"versao"}, exclude_unset=True)
    for k, v in dados.items():
        setattr(a, k, v)
    if a.status == "AGUARDANDO":
        a.status = "EM_ANALISE"
    a.examinador, a.dt_analise, a.versao = user.nome, date.today(), a.versao + 1
    registrar(db, "analise", a.id, "edicao", user.matricula, depois=dados)
    db.commit()
    return _dict(a)


@router.post("/{aid}/enviar-aprovacao")
def enviar(aid: int, user: Usuario = Depends(require_permission(f"{P}:entrada-manual:criar")), db: Session = Depends(get_db)):
    a = _get(db, aid)
    faltando = [n for n, v in (("resultado", a.resultado), ("erro percentual", a.erro_percentual), ("número do lacre", a.lacre_numero),
                               ("integridade do lacre", a.lacre_integro)) if v is None]
    if faltando:
        raise HTTPException(422, f"Preencha antes de enviar: {', '.join(faltando)}.")
    if a.resultado == "IRREGULAR" and not a.irregularidade:
        raise HTTPException(422, "Resultado irregular exige o tipo de irregularidade.")
    if a.resultado == "REGULAR" and (abs(a.erro_percentual) > LIMITE_ERRO or a.lacre_integro is False):
        raise HTTPException(422, f"Erro acima de ±{LIMITE_ERRO:g}% ou lacre violado não pode ser REGULAR.")
    _transicao(a, "AGUARDANDO_APROVACAO")
    registrar(db, "analise", a.id, "enviada_aprovacao", user.matricula)
    notificar_permissao(db, f"{P}:aprovar", "Análise aguardando aprovação", f"{a.protocolo} ({a.medidor.serie})", "/laboratorio-medidores/aprovacoes")
    db.commit()
    return _dict(a)


@router.get("/{aid}/laudo", response_class=HTMLResponse)
def laudo(aid: int, _: Usuario = Depends(require_permission(f"{P}:relatorios:visualizar")), db: Session = Depends(get_db)):
    a = _get(db, aid)
    if a.status != "APROVADA":
        raise HTTPException(409, "O laudo só é emitido após a aprovação.")
    d = {k: html.escape(str(v if v is not None else "—")) for k, v in _dict(a).items()}
    return f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Laudo {d['numero_laudo']}</title>
<style>body{{font-family:system-ui;max-width:760px;margin:32px auto;color:#1b2b2b}}h1{{color:#0f5e5c}}
table{{width:100%;border-collapse:collapse}}td{{border:1px solid #cfdcdc;padding:6px 10px}}td:first-child{{background:#eef5f4;width:40%}}
.aviso{{margin-top:24px;font-size:12px;color:#5b6b6b}}</style>
<h1>Laudo técnico {d['numero_laudo']}</h1><p>SIME · Laboratório de Medidores — documento acadêmico com dados fictícios.</p>
<table><tr><td>Protocolo</td><td>{d['protocolo']}</td></tr><tr><td>Medidor</td><td>{d['medidor']} — {d['fabricante']} {d['modelo']}</td></tr>
<tr><td>Instalação</td><td>{d['instalacao']}</td></tr><tr><td>Solicitante</td><td>{d['solicitante']}</td></tr>
<tr><td>Data da análise</td><td>{d['dt_analise']}</td></tr><tr><td>Erro de exatidão</td><td>{d['erro_percentual']} %</td></tr>
<tr><td>Lacre</td><td>{d['lacre_numero']} (íntegro: {d['lacre_integro']})</td></tr><tr><td>Resultado</td><td><b>{d['resultado']}</b></td></tr>
<tr><td>Irregularidade</td><td>{d['irregularidade']}</td></tr><tr><td>Observação</td><td>{d['observacao']}</td></tr>
<tr><td>Examinado por</td><td>{d['examinador']}</td></tr><tr><td>Aprovado por</td><td>{d['aprovador']}</td></tr></table>
<p class="aviso">Gerado em {date.today():%d/%m/%Y}. Use Imprimir → Salvar como PDF.</p><script>window.onload=()=>window.print()</script></html>"""
