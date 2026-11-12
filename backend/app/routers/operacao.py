"""Console de telemetria, consulta CCEE simulada, comissionamento SMC e monitoramento do bot."""
from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.db import get_db
from app.core.security import require_permission
from app.integrations.simulador import chamar
from app.models import JobRun, Medidor, TelemetriaDiaria, Usuario
from app.services import jobs

router = APIRouter(tags=["operacao"])
COMANDOS = ["LEITURA_INSTANTANEA", "SINCRONIZAR_RELOGIO", "REINICIAR_REMOTA", "STATUS_SINAL"]


# ===================================================== Console de telemetria
@router.get("/api/telemetria/pesquisar")
def pesquisar(ssn: str, _: Usuario = Depends(require_permission("telemetria:visualizar")), db: Session = Depends(get_db)):
    modo = chamar(db, "headend")
    m = db.query(Medidor).filter((Medidor.ssn == ssn.strip().upper()) | (Medidor.serie == ssn.strip().upper())).first()
    if not m or modo == "vazio":
        raise HTTPException(404, "SSN não encontrado no head-end.")
    tel = db.query(TelemetriaDiaria).filter_by(medidor_id=m.id).order_by(TelemetriaDiaria.data.desc()).limit(14).all()
    return {"ssn": m.ssn, "serie": m.serie, "modelo": m.modelo, "firmware": m.firmware, "tecnologia": m.tecnologia,
            "operadora": m.operadora, "status": m.status_comunicacao, "sinal_dbm": m.ultimo_sinal_dbm,
            "instalacao": m.instalacao.codigo if m.instalacao else None,
            "online_pct_14d": round(100 * sum(t.comunicou for t in tel) / len(tel), 1) if tel else None,
            "ultimas": [{"data": t.data.isoformat(), "comunicou": t.comunicou, "leituras": t.leituras_recebidas} for t in tel]}


class Execucao(BaseModel):
    comando: str
    ssns: list[str] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _v(self):
        if self.comando not in COMANDOS:
            raise ValueError(f"comando deve ser um de {COMANDOS}")
        self.ssns = list(dict.fromkeys(s.strip().upper() for s in self.ssns if s.strip()))
        return self


def _run(r: JobRun) -> dict:
    return {"id": r.id, "job_key": r.job_key, "status": r.status, "progresso": r.progresso, "parametros": r.parametros,
            "resultado": r.resultado, "disparado_por": r.disparado_por, "iniciado_em": r.iniciado_em.isoformat(),
            "finalizado_em": r.finalizado_em.isoformat() if r.finalizado_em else None}


@router.post("/api/telemetria/execucoes", status_code=202)
def criar_execucao(body: Execucao, user: Usuario = Depends(require_permission("telemetria:executar")), db: Session = Depends(get_db)):
    run = jobs.disparar(db, "console_telemetria", body.model_dump(), usuario=user.matricula)
    registrar(db, "telemetria", run.id, "execucao", user.matricula, depois=body.model_dump())
    db.commit()
    return _run(run)


@router.get("/api/telemetria/execucoes")
def execucoes(_: Usuario = Depends(require_permission("telemetria:visualizar")), db: Session = Depends(get_db)):
    return [_run(r) for r in db.query(JobRun).filter_by(job_key="console_telemetria").order_by(JobRun.id.desc()).limit(50)]


@router.get("/api/telemetria/comandos")
def comandos(_: Usuario = Depends(require_permission("telemetria:visualizar"))):
    return COMANDOS


# ============================================================ CCEE simulada
class ConsultaCcee(BaseModel):
    codigo: str = Field(min_length=10, max_length=10, description="Código SCDE (4 letras + 6 dígitos)")
    tipo: str = "P"
    inicio: date
    fim: date
    integralizacao: str = "60min"
    inverter: bool = False

    @model_validator(mode="after")
    def _v(self):
        if not re.fullmatch(r"[A-Z]{4}\d{6}", self.codigo.upper()):
            raise ValueError("Código SCDE deve ter 4 letras e 6 dígitos.")
        if self.tipo not in ("P", "R") or self.integralizacao not in ("5min", "60min"):
            raise ValueError("tipo P/R e integralização 5min/60min.")
        if self.fim < self.inicio:
            raise ValueError("Data final anterior à inicial.")
        if (self.fim - self.inicio).days > 31:
            raise ValueError("Período máximo de 31 dias por consulta.")
        if self.fim > date.today():
            raise ValueError("A câmara só disponibiliza medições até hoje.")
        self.codigo = self.codigo.upper()
        return self


def curva_ccee(c: ConsultaCcee) -> list[dict]:
    """Curva de carga determinística a partir do código (mesma consulta = mesmo resultado)."""
    semente = int(hashlib.sha256(c.codigo.encode()).hexdigest()[:8], 16)
    base = 200 + semente % 1800  # kW
    passo = 5 if c.integralizacao == "5min" else 60
    out = []
    t = datetime.combine(c.inicio, datetime.min.time())
    fim = datetime.combine(c.fim, datetime.min.time()) + timedelta(days=1)
    while t < fim:
        h = t.hour + t.minute / 60
        util = 0.35 + 0.65 * max(0.0, math.sin((h - 6) / 14 * math.pi)) if 6 <= h <= 20 else 0.35
        if t.weekday() >= 5:
            util *= 0.55
        ruido = ((semente ^ int(t.timestamp() // 300)) % 1000) / 1000 * 0.08 - 0.04
        kw = base * (util + ruido) * (0.98 if c.tipo == "R" else 1)
        kwh = kw * passo / 60
        ativa = -kwh if c.inverter else kwh
        out.append({"instante": t.isoformat(timespec="minutes"), "ativa_kwh": round(ativa, 3), "reativa_kvarh": round(kwh * 0.31, 3)})
        t += timedelta(minutes=passo)
    return out


@router.post("/api/medicao/ccee/consultas")
def consultar_ccee(body: ConsultaCcee, user: Usuario = Depends(require_permission("medicao:ccee:visualizar")), db: Session = Depends(get_db)):
    modo = chamar(db, "ccee")
    pontos = [] if modo == "vazio" else curva_ccee(body)
    registrar(db, "ccee", 0, "consulta", user.matricula, depois=body.model_dump(mode="json") | {"pontos": len(pontos)})
    db.commit()
    total = sum(p["ativa_kwh"] for p in pontos)
    return {"consulta": body.model_dump(mode="json"), "pontos": pontos, "total_kwh": round(total, 2),
            "demanda_max_kw": round(max((abs(p["ativa_kwh"]) * (60 / (5 if body.integralizacao == "5min" else 60)) for p in pontos), default=0), 1)}


@router.post("/api/medicao/ccee/consultas/csv")
def consultar_ccee_csv(body: ConsultaCcee, _: Usuario = Depends(require_permission("medicao:ccee:visualizar")), db: Session = Depends(get_db)):
    chamar(db, "ccee")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["instante", "ativa_kwh", "reativa_kvarh"])
    for p in curva_ccee(body):
        w.writerow([p["instante"], str(p["ativa_kwh"]).replace(".", ","), str(p["reativa_kvarh"]).replace(".", ",")])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="ccee_{body.codigo}{body.tipo}.csv"'})


# ========================================================== Comissionamento
class Comissionamento(BaseModel):
    pares: str = Field(min_length=3, max_length=100_000)


@router.post("/api/smc/comissionamento", status_code=202)
def comissionar(body: Comissionamento, user: Usuario = Depends(require_permission("smc:comissionamento:visualizar")), db: Session = Depends(get_db)):
    try:
        run = jobs.disparar(db, "comissionamento", {"pares": body.pares}, usuario=user.matricula)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return _run(run)


# ==================================================== Monitoramento do bot
@router.get("/api/comunicacao-campo/bot/monitoramento")
def monitoramento_bot(horas: int = 6, _: Usuario = Depends(require_permission("comunicacao-campo:monitoramento-bot:visualizar")),
                      db: Session = Depends(get_db)):
    modo = chamar(db, "bot")
    agora = datetime.now().replace(second=0, microsecond=0)
    pontos = []
    if modo != "vazio":
        for k in range(horas * 12, -1, -1):
            t = agora - timedelta(minutes=5 * k)
            x = t.timestamp() / 3600
            cpu = 18 + 12 * math.sin(x / 2) + 6 * math.sin(x * 3.1) + (25 if t.hour in (8, 9, 14) else 0)
            mem = 41 + 4 * math.sin(x / 5) + (t.minute % 30) / 10
            pontos.append({"instante": t.isoformat(timespec="minutes"), "cpu_pct": round(max(1, min(99, cpu)), 1),
                           "memoria_pct": round(mem, 1)})
    return {"pontos": pontos, "alerta": any(p["cpu_pct"] > 80 for p in pontos[-6:])}
