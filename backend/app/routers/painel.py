"""Painel geral, Visão 360 da Instalação e Gestão MT (diagnóstico, mapa, plano de campo)."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import median

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.db import get_db
from app.core.security import require_permission
from app.models import (AcaoRecomendada, Analise, ConsumoMensal, Erb, Instalacao, Medidor, Registro, RelatorioSnapshot,
                        TelemetriaDiaria, TrocaMedidor, Usuario)
from app.rules import diagnostico_mt as regras_mt
from app.rules import visao360 as regras360

router = APIRouter(tags=["painel"])


# =================================================================== Painel
@router.get("/api/dashboard/resumo")
def resumo(regional: str | None = None, tecnologia: str | None = None, dias: int = Query(30, ge=7, le=30),
           _: Usuario = Depends(require_permission("dashboard:visualizar")), db: Session = Depends(get_db)):
    qm = db.query(Medidor).join(Instalacao, isouter=True).filter(Medidor.situacao == "INSTALADO")
    if regional:
        qm = qm.filter(Instalacao.regional == regional)
    if tecnologia:
        qm = qm.filter(Medidor.tecnologia == tecnologia)
    meds = qm.all()
    ids = {m.id for m in meds}
    st = Counter(m.status_comunicacao for m in meds)
    ultimo = db.query(func.max(TelemetriaDiaria.data)).scalar() or date.today()
    serie_com = []
    for dia, total, ok in (db.query(TelemetriaDiaria.data, func.count(), func.sum(cast(TelemetriaDiaria.comunicou, Integer)))
                           .filter(TelemetriaDiaria.data > ultimo - timedelta(days=dias), TelemetriaDiaria.medidor_id.in_(ids))
                           .group_by(TelemetriaDiaria.data).order_by(TelemetriaDiaria.data)):
        serie_com.append({"data": dia.isoformat(), "percentual": round(100 * (ok or 0) / total, 1) if total else 0})
    qi = db.query(Instalacao)
    if regional:
        qi = qi.filter(Instalacao.regional == regional)
    inst_ids = [i.id for i in qi.all()]
    consumo = [{"referencia": r.isoformat()[:7], "mwh": round((k or 0) / 1000, 1)} for r, k in
               db.query(ConsumoMensal.referencia, func.sum(ConsumoMensal.kwh)).filter(ConsumoMensal.instalacao_id.in_(inst_ids))
               .group_by(ConsumoMensal.referencia).order_by(ConsumoMensal.referencia).all()][-12:]
    regs = Counter((r.recurso, (r.dados or {}).get("status")) for r in db.query(Registro).filter(
        Registro.recurso.in_(["smc_programacoes_nota", "smc_recapacitacao", "sugestoes"])).all())
    analises = Counter(a for (a,) in db.query(Analise.status).all())
    return {
        "filtros": {"regional": regional, "tecnologia": tecnologia, "dias": dias},
        "kpis": {
            "instalacoes": len(inst_ids), "medidores": len(meds),
            "comunicando_pct": round(100 * st.get("COMUNICANDO", 0) / len(meds), 1) if meds else 0,
            "risco_alto": sum(1 for m in meds if m.risco_falha >= regras_mt.RISCO_ALTO),
            "analises_pendentes": sum(v for k, v in analises.items() if k != "APROVADA"),
            "programacoes_abertas": regs.get(("smc_programacoes_nota", "ABERTA"), 0) + regs.get(("smc_programacoes_nota", "PROGRAMADO"), 0),
            "recapacitacoes_abertas": sum(v for (r, s), v in regs.items() if r == "smc_recapacitacao" and s not in ("concluida", "cancelada")),
            "sugestoes_abertas": sum(v for (r, s), v in regs.items() if r == "sugestoes" and s not in ("concluida", "rejeitada", "duplicada")),
        },
        "status_comunicacao": [{"status": k, "quantidade": v} for k, v in st.most_common()],
        "por_tecnologia": [{"tecnologia": k, "quantidade": v} for k, v in Counter(m.tecnologia for m in meds).most_common()],
        "serie_comunicacao": serie_com, "consumo_mensal": consumo,
        "analises_por_status": [{"status": k, "quantidade": v} for k, v in analises.most_common()],
        "regionais": sorted({r for (r,) in db.query(Instalacao.regional).distinct()}),
    }


# =============================================================== Visão 360
def _dossie(db: Session, inst: Instalacao) -> regras360.Dossie:
    serie = [regras360.Mes(c.referencia, c.kwh, c.valor_rs, c.adicionais_rs, c.tipo_leitura, c.gerado_kwh, c.injetado_kwh, c.credito_kwh)
             for c in db.query(ConsumoMensal).filter_by(instalacao_id=inst.id).order_by(ConsumoMensal.referencia)]
    viz_ids = [i for (i,) in db.query(Instalacao.id).filter(Instalacao.bairro == inst.bairro, Instalacao.municipio == inst.municipio,
                                                            Instalacao.categoria == inst.categoria, Instalacao.id != inst.id)]
    ref_min = (date.today().replace(day=1) - timedelta(days=185)).replace(day=1)
    viz = [k for (k,) in db.query(func.avg(ConsumoMensal.kwh)).filter(ConsumoMensal.instalacao_id.in_(viz_ids),
                                                                      ConsumoMensal.referencia >= ref_min).group_by(ConsumoMensal.instalacao_id)]
    perfil_inj = None
    if inst.mmgd:
        pares = (db.query(Instalacao.mmgd_kwp, func.avg(ConsumoMensal.injetado_kwh)).join(ConsumoMensal)
                 .filter(Instalacao.mmgd.is_(True), Instalacao.categoria == inst.categoria, ConsumoMensal.injetado_kwh.isnot(None))
                 .group_by(Instalacao.id).all())
        vals = [inj / kwp for kwp, inj in pares if kwp and inj]
        perfil_inj = median(vals) if vals else None
    trocas = [{"data": t.data.strftime("%d/%m/%Y"), "serie_retirada": t.serie_retirada, "serie_instalada": t.serie_instalada, "motivo": t.motivo}
              for t in db.query(TrocaMedidor).filter_by(instalacao_id=inst.id).order_by(TrocaMedidor.data)]
    return regras360.Dossie(inst.codigo, inst.categoria, inst.classe_tarifaria, inst.classe_anterior, inst.data_mudanca_classe,
                            inst.titular_desde, inst.mmgd, inst.mmgd_kwp, inst.mmgd_desde, serie, trocas,
                            median(viz) if len(viz) >= 3 else None, perfil_inj)


@router.get("/api/visao-360/busca")
def busca_360(q: str = Query(min_length=3), _: Usuario = Depends(require_permission("visao-360:visualizar")), db: Session = Depends(get_db)):
    termo = q.strip()
    insts = db.query(Instalacao).filter(Instalacao.codigo.like(f"{termo}%")).limit(15).all()
    if not insts:
        med = db.query(Medidor).filter((Medidor.serie == termo) | (Medidor.ssn == termo)).first()
        insts = [med.instalacao] if med and med.instalacao else []
    if not insts:
        insts = db.query(Instalacao).filter(Instalacao.cliente.ilike(f"%{termo}%")).limit(15).all()
    return [{"codigo": i.codigo, "cliente": i.cliente, "municipio": i.municipio, "categoria": i.categoria} for i in insts]


def _montar_360(db: Session, codigo: str) -> dict:
    inst = db.query(Instalacao).filter_by(codigo=codigo).first()
    if not inst:
        raise HTTPException(404, f"Instalação {codigo} não encontrada.")
    dossie = _dossie(db, inst)
    diag = regras360.diagnosticar(dossie)
    meds = [{"serie": m.serie, "ssn": m.ssn, "modelo": m.modelo, "fabricante": m.fabricante, "tecnologia": m.tecnologia,
             "operadora": m.operadora, "status_comunicacao": m.status_comunicacao, "ultimo_sinal_dbm": m.ultimo_sinal_dbm,
             "risco_falha": m.risco_falha} for m in inst.medidores]
    series = [m.serie for m in inst.medidores]
    ligados = {"analises": [{"protocolo": a.protocolo, "status": a.status, "resultado": a.resultado, "laudo": a.numero_laudo}
                            for a in db.query(Analise).filter_by(instalacao_codigo=codigo)],
               "registros": [{"recurso": r.recurso, "id": r.id, "status": (r.dados or {}).get("status") or (r.dados or {}).get("situacao")}
                             for r in db.query(Registro).all() if (r.dados or {}).get("instalacao") == codigo or (r.dados or {}).get("medidor") in series][:50]}
    return {
        "instalacao": {"codigo": inst.codigo, "cliente": inst.cliente, "documento": inst.documento, "categoria": inst.categoria,
                       "classe_tarifaria": inst.classe_tarifaria, "tensao": inst.tensao, "mercado": inst.mercado,
                       "endereco": f"{inst.endereco} — {inst.bairro}, {inst.municipio}", "regional": inst.regional,
                       "situacao": inst.situacao, "data_ligacao": inst.data_ligacao.isoformat(), "titular_desde": inst.titular_desde.isoformat(),
                       "mmgd": inst.mmgd, "mmgd_kwp": inst.mmgd_kwp, "mmgd_desde": inst.mmgd_desde.isoformat() if inst.mmgd_desde else None,
                       "lat": inst.lat, "lon": inst.lon},
        "medidores": meds, "trocas": dossie.trocas,
        "serie": [{"referencia": m.referencia.isoformat()[:7], "kwh": m.kwh, "valor_rs": m.valor_rs, "tipo_leitura": m.tipo_leitura,
                   "gerado_kwh": m.gerado_kwh, "injetado_kwh": m.injetado_kwh} for m in dossie.serie],
        "vizinhanca_mediana_kwh": dossie.mediana_vizinhanca_kwh, "diagnostico": diag, "vinculos": ligados,
    }


@router.get("/api/visao-360/dossie/{codigo}")
def dossie_360(codigo: str, user: Usuario = Depends(require_permission("visao-360:visualizar")), db: Session = Depends(get_db)):
    out = _montar_360(db, codigo)
    registrar(db, "visao360", 0, "consulta", user.matricula, texto=codigo)  # trilha de privacidade
    db.commit()
    return out


@router.post("/api/visao-360/relatorios", status_code=201)
def gerar_relatorio(codigo: str, user: Usuario = Depends(require_permission("visao-360:exportar")), db: Session = Depends(get_db)):
    """Congela o dossiê num snapshot imutável identificado pelo SHA-256 do conteúdo."""
    conteudo = _montar_360(db, codigo)
    conteudo["gerado_por"], conteudo["gerado_em"] = user.matricula, date.today().isoformat()
    sha = hashlib.sha256(json.dumps(conteudo, sort_keys=True, default=str).encode()).hexdigest()
    if not db.get(RelatorioSnapshot, sha):
        db.add(RelatorioSnapshot(sha256=sha, instalacao_codigo=codigo, conteudo=conteudo, usuario=user.matricula))
        db.commit()
    return {"sha256": sha}


@router.get("/api/visao-360/relatorios")
def listar_relatorios(_: Usuario = Depends(require_permission("visao-360:visualizar")), db: Session = Depends(get_db)):
    return [{"sha256": r.sha256, "instalacao": r.instalacao_codigo, "usuario": r.usuario, "em": r.em.isoformat()}
            for r in db.query(RelatorioSnapshot).order_by(RelatorioSnapshot.em.desc()).limit(100)]


@router.get("/api/visao-360/relatorios/{sha}")
def obter_relatorio(sha: str, _: Usuario = Depends(require_permission("visao-360:visualizar")), db: Session = Depends(get_db)):
    r = db.get(RelatorioSnapshot, sha)
    if not r:
        raise HTTPException(404, "Relatório não encontrado.")
    return r.conteudo


@router.get("/api/visao-360/exportar/{codigo}")
def exportar_360(codigo: str, _: Usuario = Depends(require_permission("visao-360:exportar")), db: Session = Depends(get_db)):
    d = _montar_360(db, codigo)
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf, delimiter=";")
    w.writerow(["referencia", "kwh", "valor_rs", "tipo_leitura", "gerado_kwh", "injetado_kwh"])
    for m in d["serie"]:
        w.writerow([m["referencia"], m["kwh"], m["valor_rs"], m["tipo_leitura"], m["gerado_kwh"] or "", m["injetado_kwh"] or ""])
    w.writerow([])
    w.writerow(["codigo_regra", "titulo", "severidade", "descricao"])
    for a in d["diagnostico"]["achados"]:
        w.writerow([a["codigo"], a["titulo"], a["severidade"], a["descricao"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="visao360_{codigo}.csv"'})


@router.get("/api/visao-360/regras")
def regras_360(_: Usuario = Depends(require_permission("visao-360:visualizar"))):
    return [{"codigo": c, "grupo": g, "descricao": (f.__doc__ or "").strip()} for c, g, f in regras360.REGRAS]


# ================================================================ Gestão MT
def _med_dict(m: Medidor) -> dict:
    i = m.instalacao
    return {"serie": m.serie, "ssn": m.ssn, "modelo": m.modelo, "tecnologia": m.tecnologia, "operadora": m.operadora,
            "status_comunicacao": m.status_comunicacao, "ultimo_sinal_dbm": m.ultimo_sinal_dbm, "risco_falha": m.risco_falha,
            "instalacao": i.codigo if i else None, "municipio": i.municipio if i else None, "tensao": i.tensao if i else None,
            "lat": i.lat if i else None, "lon": i.lon if i else None}


@router.get("/api/gestao-mt/dashboard")
def dashboard_mt(_: Usuario = Depends(require_permission("gestao-mt:dashboard:visualizar")), db: Session = Depends(get_db)):
    meds = db.query(Medidor).join(Instalacao).filter(Instalacao.tensao == "MT", Medidor.situacao == "INSTALADO").all()
    dataref = db.query(func.max(AcaoRecomendada.dataref)).scalar()
    acoes = db.query(AcaoRecomendada).filter_by(dataref=dataref).all() if dataref else []
    faixas = Counter("0-30" if m.risco_falha < 30 else "30-70" if m.risco_falha < 70 else "70-100" for m in meds)
    por_op: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for m in meds:
        por_op[m.operadora or "—"][0] += 1
        por_op[m.operadora or "—"][1] += int(m.status_comunicacao == "COMUNICANDO")
    return {"dataref": dataref.isoformat() if dataref else None, "medidores_mt": len(meds),
            "status": [{"status": k, "quantidade": v} for k, v in Counter(m.status_comunicacao for m in meds).most_common()],
            "faixas_risco": [{"faixa": f, "quantidade": faixas.get(f, 0)} for f in ("0-30", "30-70", "70-100")],
            "acoes": [{"codigo": k, "quantidade": v} for k, v in Counter(a.codigo for a in acoes).most_common()],
            "operadoras": [{"operadora": k, "medidores": v[0], "comunicando_pct": round(100 * v[1] / v[0], 1)} for k, v in por_op.items()]}


@router.get("/api/gestao-mt/diagnostico")
def diagnostico_lista(codigo: str | None = None, confianca: str | None = None, tensao: str | None = None, q: str | None = None,
                      _: Usuario = Depends(require_permission("gestao-mt:diagnostico:visualizar")), db: Session = Depends(get_db)):
    dataref = db.query(func.max(AcaoRecomendada.dataref)).scalar()
    if not dataref:
        return {"dataref": None, "itens": []}
    qa = db.query(AcaoRecomendada).filter_by(dataref=dataref)
    if codigo:
        qa = qa.filter_by(codigo=codigo)
    if confianca:
        qa = qa.filter_by(confianca=confianca)
    itens = []
    for a in qa.all():
        md = _med_dict(a.medidor)
        if tensao and md["tensao"] != tensao:
            continue
        if q and q.lower() not in f"{md['serie']} {md['instalacao']} {md['ssn']}".lower():
            continue
        itens.append({"id": a.id, "codigo": a.codigo, "titulo": a.titulo, "texto": a.texto, "justificativa": a.justificativa,
                      "confianca": a.confianca, "sintoma": a.sintoma, "medidor": md})
    itens.sort(key=lambda x: -x["medidor"]["risco_falha"])
    return {"dataref": dataref.isoformat(), "itens": itens}


@router.get("/api/gestao-mt/medidor/{serie}")
def diagnostico_medidor(serie: str, _: Usuario = Depends(require_permission("gestao-mt:diagnostico:visualizar")), db: Session = Depends(get_db)):
    m = db.query(Medidor).filter((Medidor.serie == serie) | (Medidor.ssn == serie)).first()
    if not m:
        raise HTTPException(404, "Medidor não encontrado.")
    tel = db.query(TelemetriaDiaria).filter_by(medidor_id=m.id).order_by(TelemetriaDiaria.data).all()
    acao = db.query(AcaoRecomendada).filter_by(medidor_id=m.id).order_by(AcaoRecomendada.dataref.desc()).first()
    enlaces = []
    if m.instalacao and m.tecnologia == "CELULAR":
        ctx = regras_mt.Contexto(m.serie, m.status_comunicacao, m.operadora, m.ultimo_sinal_dbm, None, 0, m.modelo,
                                 lat=m.instalacao.lat, lon=m.instalacao.lon)
        enlaces = [e.__dict__ for e in regras_mt.testar_enlaces(ctx, [
            {"codigo": e.codigo, "operadora": e.operadora, "lat": e.lat, "lon": e.lon, "potencia_dbm": e.potencia_dbm} for e in db.query(Erb)])]
    return {"medidor": _med_dict(m), "telemetria": [{"data": t.data.isoformat(), "comunicou": t.comunicou, "sinal_dbm": t.sinal_dbm,
                                                     "leituras": t.leituras_recebidas} for t in tel[-30:]],
            "acao": {"codigo": acao.codigo, "titulo": acao.titulo, "texto": acao.texto, "justificativa": acao.justificativa,
                     "confianca": acao.confianca, "dataref": acao.dataref.isoformat()} if acao else None,
            "enlaces": enlaces}


@router.get("/api/gestao-mt/mapa")
def mapa(municipio: str | None = None, _: Usuario = Depends(require_permission("gestao-mt:mapa:visualizar")), db: Session = Depends(get_db)):
    q = db.query(Medidor).join(Instalacao).filter(Medidor.tecnologia == "CELULAR", Medidor.situacao == "INSTALADO")
    if municipio:
        q = q.filter(Instalacao.municipio == municipio)
    erbs = db.query(Erb).all() if not municipio else db.query(Erb).filter_by(municipio=municipio).all()
    return {"medidores": [_med_dict(m) for m in q.all()],
            "erbs": [{"codigo": e.codigo, "operadora": e.operadora, "tecnologia": e.tecnologia, "lat": e.lat, "lon": e.lon} for e in erbs]}


@router.post("/api/gestao-mt/plano-campo/gerar")
def gerar_plano(user: Usuario = Depends(require_permission("gestao-mt:plano-campo:criar")), db: Session = Depends(get_db)):
    """Transforma as ações que exigem visita em itens do Plano de Campo (sem duplicar)."""
    dataref = db.query(func.max(AcaoRecomendada.dataref)).scalar()
    if not dataref:
        raise HTTPException(409, "Nenhum diagnóstico disponível. Rode a rotina de diagnóstico.")
    campo = {"SUBSTITUIR_MEDIDOR", "INSPECIONAR_CABO", "VISITA_TECNICA", "ANTENA_EXTERNA", "VERIFICAR_ANTENA", "TROCAR_OPERADORA"}
    existentes = {(r.dados or {}).get("medidor") for r in db.query(Registro).filter_by(recurso="mt_plano_campo").all()
                  if (r.dados or {}).get("status") in ("PLANEJADO", "EM_CAMPO")}
    criados = 0
    for a in db.query(AcaoRecomendada).filter_by(dataref=dataref).all():
        if a.codigo not in campo or a.medidor.serie in existentes or not a.medidor.instalacao:
            continue
        r = Registro(recurso="mt_plano_campo", criado_por=user.matricula, dados={
            "instalacao": a.medidor.instalacao.codigo, "medidor": a.medidor.serie, "acao_codigo": a.codigo,
            "prioridade": {"ALTA": "ALTA", "MEDIA": "MEDIA"}.get(a.confianca, "BAIXA"),
            "data_prevista": (dataref + timedelta(days=2 if a.confianca == "ALTA" else 5)).isoformat(), "equipe": None, "status": "PLANEJADO"})
        db.add(r)
        db.flush()
        registrar(db, "mt_plano_campo", r.id, "criacao", user.matricula, depois=r.dados, texto="gerado do diagnóstico")
        criados += 1
    db.commit()
    return {"criados": criados, "dataref": dataref.isoformat()}
