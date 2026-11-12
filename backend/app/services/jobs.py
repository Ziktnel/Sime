"""Rotinas (jobs) com execução em segundo plano, cancelamento, log e agendamento diário."""
from __future__ import annotations

import random
import threading
import time
from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import db as dbmod
from app.core.auditoria import notificar_permissao
from app.integrations.simulador import IntegracaoIndisponivel, chamar
from app.models import Agendamento, JobRun, Medidor, Registro, TelemetriaDiaria, Usuario, agora
from app.services import diagnostico


class Cancelado(Exception):
    pass


class Ctx:
    def __init__(self, db: Session, run: JobRun) -> None:
        self.db, self.run = db, run

    def log(self, texto: str) -> None:
        self.run.log += f"[{datetime.now():%H:%M:%S}] {texto}\n"
        self.db.commit()

    def progresso(self, pct: int) -> None:
        self.db.refresh(self.run)
        if self.run.status == "cancelled":
            raise Cancelado()
        self.run.progresso = max(0, min(100, pct))
        self.db.commit()


# ------------------------------------------------------------------ rotinas
def job_diagnostico(c: Ctx, p: dict) -> dict:
    db = c.db
    ultimo = db.query(func.max(TelemetriaDiaria.data)).scalar()
    dia = date.fromisoformat(p["data"]) if p.get("data") else (ultimo + timedelta(days=1) if ultimo else date.today())
    c.log(f"Coletando telemetria simulada do dia {dia:%d/%m/%Y} (head-end)")
    chamar(db, "headend")
    c.progresso(20)
    n = diagnostico.simular_dia(db, dia, random.Random(dia.toordinal()))
    db.commit()
    c.log(f"{n} medidores com telemetria registrada")
    c.progresso(55)
    c.log("Recalculando status, risco de falha e ação recomendada final")
    res = diagnostico.recalcular(db, dia)
    c.progresso(90)
    notificar_permissao(db, "gestao-mt:diagnostico:visualizar", "Diagnóstico diário concluído",
                        f"{res.get('acoes', 0)} ações recomendadas para {dia:%d/%m/%Y}.", "/gestao-mt/diagnostico")
    db.commit()
    return res


def job_base_mdm(c: Ctx, p: dict) -> dict:
    db = c.db
    c.log("Consultando MDM simulado")
    modo = chamar(db, "mdm")
    c.progresso(30)
    db.query(Registro).filter(Registro.recurso.in_(["medicao_base_telemedidos", "smc_base_mdm"])).delete(synchronize_session=False)
    if modo == "vazio":
        db.commit()
        c.log("MDM respondeu sem registros — bases esvaziadas")
        return {"telemedidos": 0, "smc": 0}
    medidores = db.query(Medidor).filter(Medidor.situacao == "INSTALADO", Medidor.instalacao_id.isnot(None)).all()
    hoje = date.today()
    tele = smc = 0
    for i, m in enumerate(medidores):
        st = {"COMUNICANDO": "ATIVO", "INTERMITENTE": "ATIVO"}.get(m.status_comunicacao, "SEM_LEITURA")
        if m.instalacao.tensao == "MT" or m.instalacao.mercado == "LIVRE":
            db.add(Registro(recurso="medicao_base_telemedidos", dados={
                "instalacao": m.instalacao.codigo, "medidor": m.serie, "ssn": m.ssn, "grupo_leitura": f"G{(m.id % 20) + 1:02d}",
                "ultima_leitura": (hoje - timedelta(days=0 if st == "ATIVO" else 5 + m.id % 20)).isoformat(), "status_mdm": st}))
            tele += 1
        elif m.tecnologia in ("RF_MESH", "PLC"):
            db.add(Registro(recurso="smc_base_mdm", dados={
                "medidor": m.serie, "instalacao": m.instalacao.codigo, "agrupamento": f"AGR-{(m.id % 60) + 1:04d}",
                "status_ponto": "COMUNICANDO" if st == "ATIVO" else "SEM_COMUNICACAO",
                "ultima_comunicacao": (hoje - timedelta(days=0 if st == "ATIVO" else 3 + m.id % 30)).isoformat()}))
            smc += 1
        if i % 200 == 0:
            c.progresso(30 + int(60 * i / max(1, len(medidores))))
    db.commit()
    c.log(f"Base de telemedidos: {tele} pontos; base SMC: {smc} pontos")
    return {"telemedidos": tele, "smc": smc}


def job_auditoria_vinculos(c: Ctx, p: dict) -> dict:
    db = c.db
    c.log("Consultando diretório corporativo simulado")
    chamar(db, "diretorio")
    desligados = db.query(Usuario).filter_by(vinculo_ativo=False, ativo=True).all()
    for u in desligados:
        u.ativo = False
        c.log(f"Acesso revogado: {u.matricula} (vínculo encerrado)")
    if desligados:
        notificar_permissao(db, "gerenciamento:usuarios:editar", "Auditoria de vínculos",
                            f"{len(desligados)} acesso(s) revogado(s) por vínculo encerrado.", "/gerenciamento/usuarios")
    db.commit()
    return {"revogados": len(desligados)}


def job_comissionamento(c: Ctx, p: dict) -> dict:
    db = c.db
    chamar(db, "datalake")
    linhas = [l.strip() for l in str(p.get("pares", "")).splitlines() if l.strip()]
    if not linhas:
        raise ValueError("Informe ao menos um par 'CP;medidor'.")
    saida, erros = ["cp;medidor;ssn;tecnologia;status"], 0
    for n, linha in enumerate(linhas, 1):
        partes = [x.strip() for x in linha.replace(",", ";").split(";")]
        m = db.query(Medidor).filter_by(serie=partes[1]).first() if len(partes) == 2 else None
        if not m:
            erros += 1
            saida.append(f"{partes[0]};{partes[-1]};;;ERRO: medidor não encontrado")
        else:
            saida.append(f"{partes[0]};{m.serie};{m.ssn};{m.tecnologia};{'APTO' if m.status_comunicacao == 'COMUNICANDO' else 'PENDENTE_COMUNICACAO'}")
        c.progresso(int(100 * n / len(linhas)))
        time.sleep(0.05)
    c.log(f"{len(linhas)} pares processados, {erros} com erro")
    return {"csv": "\n".join(saida), "pares": len(linhas), "erros": erros}


def job_console(c: Ctx, p: dict) -> dict:
    """Execução em massa do console de telemetria."""
    db = c.db
    chamar(db, "headend")
    comando = p.get("comando", "LEITURA_INSTANTANEA")
    ssns = p.get("ssns") or []
    rng = random.Random(hash((comando, tuple(ssns))) & 0xFFFF)
    resultados = []
    for n, ssn in enumerate(ssns, 1):
        m = db.query(Medidor).filter_by(ssn=ssn).first()
        if not m:
            st, det = "ERROR", "SSN não cadastrado"
        elif m.status_comunicacao in ("SEM COMUNICACAO",):
            st, det = "TIMEOUT", "Sem resposta da remota em 60 s"
        elif m.status_comunicacao == "MEDIDOR NAO RESPONDE":
            st, det = ("ACK", "Remota respondeu, medidor não") if rng.random() < 0.7 else ("TIMEOUT", "Sem resposta")
        else:
            st = "SUCCESS" if rng.random() < 0.93 else "TIMEOUT"
            det = {"LEITURA_INSTANTANEA": f"Energia ativa {rng.uniform(1000, 90000):.1f} kWh",
                   "SINCRONIZAR_RELOGIO": "Relógio ajustado (desvio 0,8 s)", "REINICIAR_REMOTA": "Remota reiniciada",
                   "STATUS_SINAL": f"RSSI {m.ultimo_sinal_dbm or -80:.0f} dBm"}.get(comando, "OK") if st == "SUCCESS" else "Sem resposta"
            if st == "SUCCESS" and comando == "SINCRONIZAR_RELOGIO" and m.status_comunicacao == "RELOGIO_CRITICO":
                m.status_comunicacao = "COMUNICANDO"
        resultados.append({"ssn": ssn, "status": st, "detalhe": det})
        c.log(f"{ssn}: {st} — {det}")
        c.progresso(int(100 * n / max(1, len(ssns))))
        time.sleep(0.15)
    db.commit()
    return {"comando": comando, "resultados": resultados,
            "resumo": {s: sum(1 for r in resultados if r["status"] == s) for s in {r["status"] for r in resultados}}}


JOBS: dict[str, dict] = {
    "diagnostico_diario": {"titulo": "Diagnóstico diário de medidores", "area": "Gestão MT", "fn": job_diagnostico, "horario": "07:30"},
    "atualizar_base_mdm": {"titulo": "Atualizar bases do MDM", "area": "Medição", "fn": job_base_mdm, "horario": "06:00"},
    "auditoria_vinculos": {"titulo": "Auditoria de vínculos de usuários", "area": "Gerenciamento", "fn": job_auditoria_vinculos, "horario": "08:00"},
    "comissionamento": {"titulo": "Comissionamento de medidores SMC", "area": "Medição Centralizada", "fn": job_comissionamento, "horario": None},
    "console_telemetria": {"titulo": "Execução em massa (console de telemetria)", "area": "Console de Telemetria", "fn": job_console, "horario": None},
}


def _executar(run_id: int) -> None:
    db = dbmod.SessionLocal()
    run = db.get(JobRun, run_id)
    fn: Callable = JOBS[run.job_key]["fn"]
    c = Ctx(db, run)
    try:
        c.log(f"Início: {JOBS[run.job_key]['titulo']}")
        run.resultado = fn(c, run.parametros or {})
        run.status, run.progresso = "success", 100
        c.log("Concluído com sucesso")
    except Cancelado:
        db.rollback()
        run = db.get(JobRun, run_id)
        c.run = run
        c.log("Cancelado pelo usuário")
    except IntegracaoIndisponivel as e:
        db.rollback()
        run = db.get(JobRun, run_id)
        run.status, c.run = "error", run
        c.log(f"ERRO: {e}")
    except Exception as e:  # noqa: BLE001 - o erro vai para o log da execução
        db.rollback()
        run = db.get(JobRun, run_id)
        run.status, c.run = "error", run
        c.log(f"ERRO: {e}")
    finally:
        run.finalizado_em = agora()
        db.commit()
        db.close()


def disparar(db: Session, job_key: str, parametros: dict | None = None, usuario: str = "agendador",
             sincrono: bool = False) -> JobRun:
    if job_key not in JOBS:
        raise KeyError(job_key)
    em_curso = db.query(JobRun).filter_by(job_key=job_key, status="running").first()
    if em_curso and job_key != "console_telemetria":
        raise RuntimeError(f"A rotina já está em execução (#{em_curso.id}).")
    run = JobRun(job_key=job_key, parametros=parametros or {}, disparado_por=usuario)
    db.add(run)
    db.commit()
    if sincrono:
        _executar(run.id)
        db.refresh(run)
    else:
        threading.Thread(target=_executar, args=(run.id,), daemon=True).start()
    return run


def garantir_agendamentos(db: Session) -> None:
    for chave, j in JOBS.items():
        if j["horario"] and not db.get(Agendamento, chave):
            db.add(Agendamento(job_key=chave, horario=j["horario"]))
    db.commit()


def tick_agendador(db: Session, agora_: datetime | None = None) -> list[str]:
    """Dispara rotinas cujo horário diário já passou e que ainda não rodaram hoje."""
    agora_ = agora_ or datetime.now()
    disparados = []
    for ag in db.query(Agendamento).filter_by(ativo=True).all():
        if ag.ultima_execucao == agora_.date() or agora_.strftime("%H:%M") < ag.horario:
            continue
        ag.ultima_execucao = agora_.date()
        db.commit()
        try:
            disparar(db, ag.job_key)
            disparados.append(ag.job_key)
        except RuntimeError:
            pass
    return disparados


def iniciar_agendador(intervalo_s: int = 30) -> threading.Event:
    parar = threading.Event()

    def loop() -> None:
        while not parar.wait(intervalo_s):
            db = dbmod.SessionLocal()
            try:
                tick_agendador(db)
            finally:
                db.close()

    threading.Thread(target=loop, daemon=True).start()
    return parar
