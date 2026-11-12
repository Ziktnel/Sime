"""Serviço de diagnóstico diário dos medidores (usado pela rotina e pelo seed)."""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from app.models import AcaoRecomendada, Erb, Instalacao, Medidor, TelemetriaDiaria
from app.rules import diagnostico_mt as regras

STATUS_FALHA = ("SEM COMUNICACAO", "MEDIDOR NAO RESPONDE", "INTERMITENTE", "RELOGIO_CRITICO")


def prob_comunicar(m: Medidor) -> float:
    """Probabilidade diária de comunicação de um medidor (base da simulação)."""
    if m.situacao != "INSTALADO":
        return 0.0
    p = 0.97
    s = m.ultimo_sinal_dbm
    if s is not None:
        p -= 0.35 if s <= regras.SINAL_FRACO_DBM else 0.10 if s <= regras.SINAL_BOM_DBM else 0
    if m.modelo == "KW-10":
        p -= 0.20  # modelo com taxa de falha acima do parque (cenário de demonstração)
    return max(0.02, p)


def simular_dia(db: Session, dia: date, rng: random.Random) -> int:
    """Gera a telemetria de um dia para todos os medidores instalados."""
    medidores = db.query(Medidor).filter(Medidor.situacao == "INSTALADO").all()
    db.execute(delete(TelemetriaDiaria).where(TelemetriaDiaria.data == dia))
    linhas = []
    for m in medidores:
        persistente = m.status_comunicacao in ("SEM COMUNICACAO", "MEDIDOR NAO RESPONDE") and rng.random() < 0.85
        ok = (not persistente) and rng.random() < prob_comunicar(m)
        sinal = None if m.tecnologia != "CELULAR" or m.ultimo_sinal_dbm is None else round(m.ultimo_sinal_dbm + rng.uniform(-3, 3), 1)
        linhas.append({"medidor_id": m.id, "data": dia, "comunicou": ok, "sinal_dbm": sinal,
                       "leituras_recebidas": rng.randint(88, 96) if ok else 0, "leituras_esperadas": 96})
    if linhas:
        db.execute(TelemetriaDiaria.__table__.insert(), linhas)
    return len(linhas)


def recalcular(db: Session, dataref: date | None = None) -> dict:
    """Atualiza status/risco a partir dos últimos 7 dias e grava a ação recomendada final."""
    dataref = dataref or db.query(func.max(TelemetriaDiaria.data)).scalar() or date.today()
    inicio = dataref - timedelta(days=6)
    tel = defaultdict(list)
    for t in db.query(TelemetriaDiaria).filter(TelemetriaDiaria.data.between(inicio, dataref)).all():
        tel[t.medidor_id].append(t)
    medidores = db.query(Medidor).filter(Medidor.situacao == "INSTALADO").all()
    erbs = [{"codigo": e.codigo, "operadora": e.operadora, "lat": e.lat, "lon": e.lon, "potencia_dbm": e.potencia_dbm}
            for e in db.query(Erb).all()]
    inst = {i.id: i for i in db.query(Instalacao).all()}

    # estatística de "não responde" por modelo (base da regra de substituição)
    por_modelo: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for m in medidores:
        dias = tel.get(m.id, [])
        falhou = bool(dias) and not any(t.comunicou for t in dias)
        por_modelo[m.modelo][0] += 1
        por_modelo[m.modelo][1] += int(falhou)
    total = sum(v[0] for v in por_modelo.values()) or 1
    taxa_parque = sum(v[1] for v in por_modelo.values()) / total

    db.execute(delete(AcaoRecomendada).where(AcaoRecomendada.dataref == dataref))
    contagem: Counter = Counter()
    for m in medidores:
        dias = tel.get(m.id, [])
        sem = sum(1 for t in dias if not t.comunicou)
        sinais = [t.sinal_dbm for t in dias if t.sinal_dbm is not None]
        if m.status_comunicacao != "RELOGIO_CRITICO":
            if not dias or sem == 0 or sem <= 1:
                m.status_comunicacao = "COMUNICANDO"
            elif sem == len(dias):
                m.status_comunicacao = "MEDIDOR NAO RESPONDE" if (m.tecnologia != "CELULAR" or (m.ultimo_sinal_dbm or -80) > regras.SINAL_BOM_DBM) else "SEM COMUNICACAO"
            else:
                m.status_comunicacao = "INTERMITENTE"
        n, f = por_modelo[m.modelo]
        i = inst.get(m.instalacao_id)
        ctx = regras.Contexto(
            medidor=m.serie, status_comunicacao=m.status_comunicacao, operadora=m.operadora,
            ultimo_sinal_dbm=m.ultimo_sinal_dbm, media_sinal_7d=(sum(sinais) / len(sinais)) if sinais else None,
            dias_sem_comunicar_7d=sem, modelo=m.modelo, taxa_nr_modelo=f / n if n else None, taxa_nr_parque=taxa_parque,
            troca_remota_recente=m.troca_remota_recente, lat=i.lat if i else 0, lon=i.lon if i else 0)
        m.risco_falha = regras.calcular_risco(ctx)
        contagem[m.status_comunicacao] += 1
        if m.status_comunicacao == "COMUNICANDO" and m.risco_falha < regras.RISCO_ALTO:
            continue
        enlaces = regras.testar_enlaces(ctx, erbs) if regras.precisa_simular_torres(ctx) and m.tecnologia == "CELULAR" else []
        acao = regras.decidir(ctx, enlaces)
        if acao:
            db.add(AcaoRecomendada(dataref=dataref, medidor_id=m.id, sintoma=acao.sintoma, codigo=acao.codigo,
                                   titulo=acao.titulo, texto=acao.texto, justificativa=acao.justificativa,
                                   confianca=acao.confianca, dados=acao.dados))
            contagem["acoes"] += 1
    db.commit()
    return {"dataref": dataref.isoformat(), "medidores": len(medidores), "taxa_nao_responde_parque": round(taxa_parque, 4),
            **dict(contagem)}
