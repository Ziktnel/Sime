"""Gera a base sintética (determinística pela semente) — nenhum dado real.

Uso:  python -m app.seed [--reset] [--instalacoes N]
"""
from __future__ import annotations

import argparse
import math
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core import db as dbmod
from app.core.config import get_settings
from app.core.db import Base
from app.core.security import hash_senha
from app.integrations.simulador import garantir_integracoes
from app.models import (Agendamento, Analise, ConsumoMensal, Erb, Instalacao, Medidor, Notificacao, Registro,
                        TrocaMedidor, Usuario)
from app.recursos import EQUIPES, MUNICIPIOS
from app.rules.diagnostico_mt import distancia_m, sinal_estimado
from app.services import diagnostico, jobs

SENHA_DEMO = "Ohmnia@2026"
# (município, lat, lon, regional) — municípios e coordenadas fictícios
GEO = [("Vale Verde", -20.12, -43.20, "Norte"), ("Porto Claro", -20.35, -42.85, "Litoral"),
       ("Serra Alta", -20.60, -43.55, "Serrana"), ("Rio Manso", -20.85, -43.05, "Sul"),
       ("Campo Belo do Sul", -21.05, -43.40, "Sul"), ("Nova Aurora", -20.40, -43.75, "Serrana"),
       ("Santa Luzia do Mar", -20.70, -42.70, "Litoral"), ("Pedra Azul do Norte", -19.90, -43.45, "Norte")]
assert [g[0] for g in GEO] == MUNICIPIOS
OPERADORAS = ["Aurora Tel", "Brisa Móvel", "Celta Net"]
NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gisele", "Heitor", "Iara", "João", "Karina", "Lucas",
         "Marina", "Nilo", "Olívia", "Pedro", "Queila", "Rafael", "Sofia", "Tiago", "Úrsula", "Vitor", "Yara", "Zeca"]
SOBRENOMES = ["Albuquerque", "Barros", "Campos", "Duarte", "Esteves", "Ferraz", "Gouveia", "Hora", "Lacerda", "Macedo",
              "Nogueira", "Pacheco", "Queiroz", "Rezende", "Salgado", "Teixeira", "Valente", "Xavier"]
RAMOS = ["Padaria", "Mercado", "Oficina", "Metalúrgica", "Laticínios", "Cerâmica", "Farmácia", "Hotel", "Têxtil"]
BAIRROS = ["Centro", "Jardim das Flores", "Vila Nova", "Boa Vista", "Santa Clara", "Industrial", "Alto da Serra", "Beira Rio"]
RUAS = ["Rua das Acácias", "Av. dos Pioneiros", "Rua do Comércio", "Rua Sete", "Av. Beira Rio", "Rua das Palmeiras"]
MODELOS = {  # modelo: (fabricante, tecnologias)
    "VX-200": ("Voltrix", ["RF_MESH"]), "VX-310": ("Voltrix", ["CELULAR"]), "MS-3F": ("Medtron Sul", ["CELULAR", "PLC"]),
    "KW-10": ("Kwanta", ["RF_MESH", "PLC"]), "AP-SMART": ("Ampera", ["RF_MESH", "CELULAR"]),
}
IRREGULARIDADES = ["Lacre violado", "Bobina de potencial interrompida", "Registrador adulterado", "Ponte entre bornes",
                   "Erro de exatidão acima do limite"]


def _nome(rng: random.Random) -> str:
    return f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"


def criar_usuarios(db: Session, rng: random.Random) -> None:
    hash_ = hash_senha(SENHA_DEMO)
    base = [("OH0001", "Admin Demonstração", "admin", "TI"), ("OH0002", "Gestora Operacional", "gestor", "Operação"),
            ("OH0003", "Analista de Laboratório", "analista_lab", "Laboratório"), ("OH0004", "Operador de Campo", "operador_campo", "Campo"),
            ("OH0005", "Consulta Visão 360", "consulta_360", "Atendimento")]
    for mat, nome, perfil, area in base:
        db.add(Usuario(matricula=mat, nome=nome, email=f"{mat.lower()}@ohmnia.example", perfil=perfil, area=area, senha_hash=hash_))
    for n in range(6, 26):
        perfil = rng.choice(["gestor", "analista_lab", "operador_campo", "consulta_360"])
        db.add(Usuario(matricula=f"OH{n:04d}", nome=_nome(rng), email=f"oh{n:04d}@ohmnia.example", perfil=perfil,
                       area=rng.choice(["Operação", "Laboratório", "Campo", "Atendimento"]), senha_hash=hash_,
                       vinculo_ativo=rng.random() > 0.15))


def criar_erbs(db: Session, rng: random.Random) -> list[Erb]:
    erbs = []
    for mun, lat, lon, _ in GEO:
        for op in OPERADORAS:
            for _k in range(rng.randint(1, 3)):
                erbs.append(Erb(codigo=f"ERB-{len(erbs) + 1:04d}", operadora=op, tecnologia=rng.choice(["4G", "4G", "3G"]),
                                municipio=mun, lat=lat + rng.uniform(-0.09, 0.09), lon=lon + rng.uniform(-0.09, 0.09),
                                potencia_dbm=rng.choice([43.0, 46.0])))
    db.add_all(erbs)
    db.flush()
    return erbs


def _perfil_categoria(rng: random.Random) -> tuple[str, str, str, float]:
    r = rng.random()
    if r < 0.70:
        return "RESIDENCIAL", "B1 Residencial", "BT", rng.uniform(90, 420)
    if r < 0.86:
        return "COMERCIAL", "B3 Comercial", "BT", rng.uniform(300, 2500)
    if r < 0.91:
        return "COMERCIAL", "A4 Comercial", "MT", rng.uniform(8000, 40000)
    if r < 0.96:
        return "INDUSTRIAL", "A4 Industrial", "MT", rng.uniform(15000, 90000)
    return "RURAL", "B2 Rural", "BT", rng.uniform(150, 900)


def criar_instalacoes(db: Session, rng: random.Random, n: int, erbs: list[Erb], hoje: date) -> list[tuple[Instalacao, float]]:
    out = []
    vistos: set[str] = set()
    for k in range(n):
        mun, lat, lon, reg = rng.choice(GEO)
        cat, classe, tensao, base = _perfil_categoria(rng)
        pj = cat in ("COMERCIAL", "INDUSTRIAL")
        cliente = f"{rng.choice(RAMOS)} {rng.choice(SOBRENOMES)} Ltda" if pj else _nome(rng)
        doc = f"**.***.{rng.randint(100, 999)}/0001-**" if pj else f"***.{rng.randint(100, 999)}.{rng.randint(100, 999)}-**"
        ligacao = hoje - timedelta(days=rng.randint(900, 7000))
        titular = ligacao if rng.random() > 0.12 else hoje - timedelta(days=rng.randint(120, 600))
        mmgd = tensao == "BT" and cat in ("RESIDENCIAL", "COMERCIAL") and rng.random() < 0.16
        inst = Instalacao(
            codigo=f"40{rng.randint(10_000_000, 99_999_999)}", cliente=cliente, documento=doc, categoria=cat, classe_tarifaria=classe,
            tensao=tensao, municipio=mun, regional=reg, bairro=rng.choice(BAIRROS),
            endereco=f"{rng.choice(RUAS)}, {rng.randint(10, 2500)}", lat=lat + rng.uniform(-0.07, 0.07), lon=lon + rng.uniform(-0.07, 0.07),
            situacao="LIGADA" if rng.random() > 0.03 else rng.choice(["DESLIGADA", "SUSPENSA"]), data_ligacao=ligacao,
            titular_desde=titular, mmgd=mmgd, mmgd_kwp=round(rng.uniform(3, 15), 1) if mmgd else None,
            mmgd_desde=(hoje.replace(day=1) - timedelta(days=rng.randint(200, 500))).replace(day=1) if mmgd else None,
            mercado="LIVRE" if tensao == "MT" and rng.random() < 0.35 else "CATIVO")
        if rng.random() < 0.05:
            inst.classe_anterior = "B1 Residencial" if cat == "COMERCIAL" else "B3 Comercial"
            inst.data_mudanca_classe = hoje - timedelta(days=rng.randint(60, 500))
        if inst.codigo in vistos:
            continue
        vistos.add(inst.codigo)
        db.add(inst)
        out.append((inst, base))
    db.flush()
    return out


def criar_medidores(db: Session, rng: random.Random, insts: list, erbs: list[Erb], hoje: date) -> list[Medidor]:
    meds: list[Medidor] = []

    def novo(inst: Instalacao | None) -> Medidor:
        if inst is not None and inst.tensao == "MT":
            modelo = rng.choice(["VX-310", "MS-3F", "AP-SMART"])
            tec = "CELULAR"
        else:
            modelo = rng.choice(list(MODELOS))
            tec = rng.choice(MODELOS[modelo][1])
        n = len(meds) + 1
        m = Medidor(serie=f"{MODELOS[modelo][0][:2].upper()}{rng.randint(1_000_000, 9_999_999)}{n % 10}", ssn=f"SSN{n:07d}",
                    instalacao_id=inst.id if inst else None, fabricante=MODELOS[modelo][0], modelo=modelo, tecnologia=tec,
                    firmware=rng.choice(["3.1.4", "3.2.0", "4.0.1"]), carga_programa=rng.choice(["CP-21", "CP-22", "CP-23"]),
                    versao_hardware=rng.choice(["H1", "H2"]), situacao="INSTALADO" if inst else rng.choice(["ESTOQUE", "LABORATORIO"]),
                    instalado_em=(inst.data_ligacao if inst else None))
        if tec == "CELULAR" and inst is not None:
            m.operadora = rng.choice(OPERADORAS)
            mesmas = [e for e in erbs if e.operadora == m.operadora]
            erb = min(mesmas, key=lambda e: distancia_m(inst.lat, inst.lon, e.lat, e.lon))
            m.erb_id = erb.id
            m.ultimo_sinal_dbm = round(max(-125.0, sinal_estimado(erb.potencia_dbm, distancia_m(inst.lat, inst.lon, erb.lat, erb.lon))
                                           + rng.uniform(-18, 6)), 1)
        if rng.random() < 0.02 and inst is not None:
            m.status_comunicacao = "RELOGIO_CRITICO"
        elif rng.random() < (0.15 if modelo == "KW-10" else 0.04) and inst is not None:
            m.status_comunicacao = "SEM COMUNICACAO" if tec == "CELULAR" else "MEDIDOR NAO RESPONDE"
        meds.append(m)
        return m

    for inst, _ in insts:
        if inst.situacao != "DESLIGADA":
            db.add(novo(inst))
    for _ in range(140):
        db.add(novo(None))
    db.flush()
    return meds


def criar_trocas(db: Session, rng: random.Random, insts: list, hoje: date) -> None:
    for inst, _ in rng.sample(insts, k=max(1, len(insts) // 16)):
        db.add(TrocaMedidor(instalacao_id=inst.id, serie_retirada=f"RT{rng.randint(1_000_000, 9_999_999)}",
                            serie_instalada=inst.medidores[0].serie if inst.medidores else "—",
                            data=hoje - timedelta(days=rng.randint(30, 600)), motivo=rng.choice(["DEFEITO", "IRREGULARIDADE", "MODERNIZACAO"])))


def criar_consumo(db: Session, rng: random.Random, insts: list, hoje: date) -> None:
    meses = []
    ref = hoje.replace(day=1)
    for _ in range(24):
        ref = (ref - timedelta(days=1)).replace(day=1)
        meses.append(ref)
    meses.reverse()
    linhas = []
    for inst, base in insts:
        anomalia = rng.random()
        queda_em = rng.randint(8, 20) if anomalia < 0.06 else None
        pico_em = rng.randint(3, 22) if 0.06 <= anomalia < 0.10 else None
        leitura_ruim = 0.10 <= anomalia < 0.14
        sub_geracao = rng.random() < 0.25
        tarifa = 0.62 if inst.tensao == "MT" else 0.89
        idx_titular = next((k for k, m in enumerate(meses) if m >= inst.titular_desde), None)
        for k, mes in enumerate(meses):
            saz = 1 + 0.12 * math.sin((mes.month - 1) / 12 * 2 * math.pi)
            kwh = base * saz * rng.uniform(0.92, 1.08)
            if queda_em is not None and k >= queda_em:
                kwh *= 0.30
            if pico_em is not None and k == pico_em:
                kwh *= 2.4
            if idx_titular is not None and k >= idx_titular and inst.titular_desde != inst.data_ligacao:
                kwh *= 0.6
            gerado = injetado = credito = None
            if inst.mmgd and inst.mmgd_desde and mes >= inst.mmgd_desde:
                gerado = inst.mmgd_kwp * 120 * saz * rng.uniform(0.85, 1.1) * (0.5 if sub_geracao else 1)
                injetado = gerado * 0.55
                credito = injetado * rng.uniform(0.8, 0.95)
                kwh = max(30.0, kwh - gerado * 0.45)
                if anomalia > 0.985:
                    injetado = inst.mmgd_kwp * 7 * 31 * 1.4
            tipo = "NORMAL"
            if leitura_ruim and k >= 18 and rng.random() < 0.7:
                tipo = rng.choice(["MEDIA", "ESTIMADA", "IMPEDIMENTO"])
            adicionais = kwh * tarifa * (rng.uniform(0.16, 0.3) if rng.random() < 0.03 else rng.uniform(0, 0.05))
            linhas.append({"instalacao_id": inst.id, "referencia": mes, "kwh": round(kwh, 1),
                           "valor_rs": round(kwh * tarifa + adicionais, 2), "adicionais_rs": round(adicionais, 2),
                           "tipo_leitura": tipo, "gerado_kwh": round(gerado, 1) if gerado else None,
                           "injetado_kwh": round(injetado, 1) if injetado else None, "credito_kwh": round(credito, 1) if credito else None})
    db.execute(ConsumoMensal.__table__.insert(), linhas)


def criar_analises(db: Session, rng: random.Random, meds: list[Medidor], insts: list, hoje: date) -> None:
    candidatos = [m for m in meds if m.situacao in ("LABORATORIO", "ESTOQUE")]
    examinadores = ["Analista de Laboratório", "Iara Campos", "Heitor Duarte"]
    seq_laudo = 0
    for n, m in enumerate(candidatos[:120], 1):
        entrada = hoje - timedelta(days=rng.randint(0, 150))
        st = rng.choices(["AGUARDANDO", "EM_ANALISE", "AGUARDANDO_APROVACAO", "APROVADA", "REABERTA"], [20, 15, 15, 45, 5])[0]
        a = Analise(protocolo=f"AM-{entrada.year}-{n:05d}", medidor_id=m.id, instalacao_codigo=rng.choice(insts)[0].codigo,
                    status=st, solicitante=rng.choice(["CLIENTE", "DISTRIBUIDORA", "DISTRIBUIDORA", "ORGAO_REGULADOR"]),
                    nota_servico=str(rng.randint(10_000_000, 99_999_999)), dt_entrada=entrada,
                    dt_agendada=entrada + timedelta(days=rng.randint(1, 20)))
        if st != "AGUARDANDO":
            a.dt_analise = min(hoje, entrada + timedelta(days=rng.randint(1, 25)))
            a.examinador = rng.choice(examinadores)
            irregular = rng.random() < 0.35
            a.resultado = "IRREGULAR" if irregular else "REGULAR"
            a.irregularidade = rng.choice(IRREGULARIDADES) if irregular else None
            a.erro_percentual = round(rng.uniform(-8, 8) if irregular else rng.uniform(-1.8, 1.8), 2)
            a.lacre_numero = f"LC{rng.randint(100000, 999999)}"
            a.lacre_integro = not (irregular and rng.random() < 0.6)
        if st == "APROVADA":
            seq_laudo += 1
            a.aprovador, a.numero_laudo = "Gestora Operacional", f"LAU-{a.dt_analise.year}-{seq_laudo:04d}"
            if a.resultado == "IRREGULAR":
                a.quarentena = rng.choice(["PENDENTE", "VINCULADO"])
                m.situacao = "QUARENTENA" if a.quarentena == "PENDENTE" else "DESCARTADO"
        db.add(a)


def _ri(rng: random.Random, a: int, b: int) -> int:
    return rng.randint(a, b)


def criar_registros(db: Session, rng: random.Random, insts: list, meds: list[Medidor], hoje: date) -> None:
    ins = [i for i, _ in insts]
    med_inst = [m for m in meds if m.instalacao_id]
    por_id = {i.id: i for i in ins}
    mt = [i for i in ins if i.tensao == "MT"]
    livres = [i for i in mt if i.mercado == "LIVRE"]
    cel = [m for m in med_inst if m.tecnologia == "CELULAR"]
    falhos = [m for m in med_inst if m.status_comunicacao != "COMUNICANDO"] or med_inst
    d = lambda a, b=0: (hoje - timedelta(days=_ri(rng, b, a))).isoformat()  # noqa: E731
    at = lambda: f"AT{_ri(rng, 10_000_000, 99_999_999)}"  # noqa: E731
    R: list[tuple[str, dict]] = []

    for i in livres:
        m = i.medidores[0] if i.medidores else None
        R.append(("medicao_clientes_livres", {"instalacao": i.codigo, "cliente": i.cliente, "medidor_principal": m.serie if m else None,
                  "medidor_retaguarda": None, "protocolo": rng.choice(["ABNT", "DLMS"]),
                  "ssn_ccee_principal": f"{rng.choice(['ESVV', 'MGPC', 'RJSA'])}{_ri(rng, 100000, 999999)}", "remota_principal": f"RM{_ri(rng, 1000000, 9999999)}",
                  "porta": rng.choice([4059, 5000, 2101]), "data_ultima_atualizacao": d(90)}))
    for i in mt:
        m = i.medidores[0] if i.medidores else None
        if not m:
            continue
        rtc = rng.choice([20, 40, 60, 80]); rtp = rng.choice([1, 70, 120])
        R.append(("medicao_kes", {"instalacao": i.codigo, "medidor": m.serie, "rtc": rtc, "rtp": rtp, "ke": rtc * rtp, "vigencia_inicio": d(900, 30)}))
        st_fat = {"COMUNICANDO": "OK", "INTERMITENTE": "INTERMITENTE", "MEDIDOR NAO RESPONDE": "MEDIDOR NAO RESPONDE"}.get(m.status_comunicacao, "SEM COMUNICACAO")
        if st_fat != "OK" or rng.random() < 0.15:
            R.append(("fat_triagem", {"instalacao": i.codigo, "medidor": m.serie, "ciclo": hoje.strftime("%Y-%m"), "status_faturamento": st_fat,
                      "acao": "PREVIA_REMOTA" if st_fat in ("OK", "INTERMITENTE") else "LEITURA_CAMPO", "status": "PENDENTE"}))
        R.append(("fat_agenda", {"instalacao": i.codigo, "data_leitura": (hoje + timedelta(days=_ri(rng, -5, 25))).isoformat(),
                  "grupo": f"G{_ri(rng, 1, 20):02d}", "situacao": rng.choice(["AGENDADA", "AGENDADA", "LIDA", "ATRASADA"])}))
        if rng.random() < 0.15:
            R.append(("fat_exportacao", {"instalacao": i.codigo, "ciclo": hoje.strftime("%Y-%m"), "motivo": rng.choice(["SEM_ARQUIVO", "ARQUIVO_INCOMPLETO", "PONTO_AMBIGUO"]), "status": "FILA"}))
        if rng.random() < 0.1:
            R.append(("fat_cadastro", {"instalacao": i.codigo, "divergencia": rng.choice(["PONTO_STATUS_DIVERGENTE", "MEDIDOR_DIFERENTE", "KE_DIVERGENTE"]),
                      "valor_mdm": "ATIVO", "valor_erp": "INATIVO", "status": "PENDENTE"}))
        if rng.random() < 0.25:
            R.append(("mt_controle_notas", {"nota": str(_ri(rng, 10_000_000, 99_999_999)), "instalacao": i.codigo,
                      "tipo": rng.choice(["INSPECAO", "TROCA_MEDIDOR", "TROCA_REMOTA", "LEITURA"]), "abertura": d(60),
                      "status": rng.choice(["ABERTA", "EM_EXECUCAO", "ENCERRADA"])}))
        if m.status_comunicacao != "COMUNICANDO":
            R.append(("fat_campo", {"instalacao": i.codigo, "equipe": rng.choice(EQUIPES), "data": (hoje + timedelta(days=_ri(rng, 0, 3))).isoformat(),
                      "hora_limite": "10:00", "status": "PENDENTE"}))
    for k in range(40):
        i = rng.choice(ins)
        R.append(("medicao_simplificadas", {"id_migracao": f"MIG-{k + 1:05d}", "instalacao": i.codigo, "cliente": i.cliente, "data_migracao": d(400, 10),
                  "situacao": rng.choice(["EM_ANALISE", "APTO", "APTO", "RETORNO_SOLICITADO", "RETORNADO"])}))
    for k, (mun, lat, lon, _) in enumerate(GEO):
        R.append(("medicao_subestacoes", {"codigo": f"SE-{mun[:3].upper()}", "nome": f"SE {mun}", "municipio": mun,
                  "tensao_kv": rng.choice(["69", "138"]), "medidores_fronteira": _ri(rng, 2, 12), "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}"}))
    for k in range(60):
        mun, lat, lon, _ = rng.choice(GEO)
        R.append(("smc_agrupamentos", {"agrupamento": f"AGR-{k + 1:04d}", "ssn": f"CP{_ri(rng, 100000, 999999)}", "cp": f"CP-{k + 1:03d}",
                  "tecnologia": rng.choice(["RF_MESH", "PLC"]), "csd": f"CSD-{_ri(rng, 1, 9)}", "cidade": mun,
                  "coord_x": f"{lat + rng.uniform(-.05, .05):.5f}", "coord_y": f"{lon + rng.uniform(-.05, .05):.5f}", "porta": 4059}))
    for m in rng.sample(med_inst, 70):
        i = por_id[m.instalacao_id]
        R.append(("smc_controle_cadastral", {"instalacao": i.codigo, "medidor": m.serie, "campo": rng.choice(["operadora", "modelo", "agrupamento", "endereco"]),
                  "valor_mdm": rng.choice(OPERADORAS), "valor_erp": rng.choice(OPERADORAS), "status": rng.choice(["PENDENTE", "PENDENTE", "CORRIGIDO", "IGNORADO"])}))
    for m in rng.sample(falhos, min(len(falhos), 110)):
        i = por_id[m.instalacao_id]
        st = rng.choice(["ABERTA", "ABERTA", "PROGRAMADO", "NÃO PROGRAMAR", "FINALIZADA", "INTERROMPIDA"])
        R.append(("smc_programacoes_nota", {"instalacao": i.codigo, "nota_dd": str(_ri(rng, 1_000_000_000, 9_999_999_999)) if st != "ABERTA" else None,
                  "status": st, "prioridade": str(_ri(rng, 0, 3)), "lote": _ri(rng, 1, 12), "municipio": i.municipio, "medidor": m.serie,
                  "agrupamento_id": f"AGR-{(m.id % 60) + 1:04d}", "qtd_sem_comunicacao": _ri(rng, 1, 40), "tecnologia": m.tecnologia,
                  "texto_equipe": "Verificar comunicação do medidor e da remota."}))
    for m in rng.sample(cel, min(len(cel), 45)):
        i = por_id[m.instalacao_id]
        st = rng.choice(["programada", "em_execucao", "aguardando_validacao", "concluida", "cancelada"])
        dado = {"instalacao": i.codigo, "medidor": m.serie, "equipe": rng.choice(EQUIPES), "data_programada": d(30, -10), "status": st}
        if st != "programada":
            dado["atendimento_antes"] = at()
        if st in ("aguardando_validacao", "concluida"):
            dado["atendimento_depois"] = at()
        if st == "concluida":
            dado["resultado"] = rng.choice(["substituicao_realizada", "substituicao_realizada", "execucao_parcial"])
            dado["justificativa"] = None if dado["resultado"] == "substituicao_realizada" else "Poste sem acesso para antena."
        R.append(("smc_recapacitacao", dado))
    for k in range(90):
        i = rng.choice(ins)
        R.append(("equipes_notas", {"nota": str(_ri(rng, 10_000_000, 99_999_999)), "servico": rng.choice(["SUBSTITUICAO_CS", "RECLAMACAO", "MANUTENCAO", "IP"]),
                  "instalacao": i.codigo, "equipe": rng.choice(EQUIPES), "prioridade": str(_ri(rng, 0, 3)),
                  "status": rng.choice(["PENDENTE", "PENDENTE", "EM_ROTA", "EXECUTADA", "DEVOLVIDA"]), "data": d(20)}))
    for e in EQUIPES:
        mun, lat, lon, _ = rng.choice(GEO)
        R.append(("equipes_campo", {"equipe": e, "encarregado": _nome(rng), "base": mun, "situacao": rng.choice(["DISPONIVEL", "EM_CAMPO", "EM_CAMPO", "INDISPONIVEL"]),
                  "latitude": f"{lat + rng.uniform(-.05, .05):.5f}", "longitude": f"{lon + rng.uniform(-.05, .05):.5f}"}))
    for k in range(50):
        m = rng.choice(cel)
        R.append(("lab_triagem_remotas", {"remota": f"RM{_ri(rng, 1000000, 9999999)}", "medidor": m.serie, "operadora": m.operadora,
                  "iccid": f"8955{_ri(rng, 10**14, 10**15 - 1)}0", "falha_relatada": rng.choice(["Sem sinal", "Não liga", "Reinicia sozinha", "Sem dados"]),
                  "diagnostico": rng.choice(["OK", "DEFEITO", "SEM_SINAL", "SIM_SUSPENSO", None]), "status": rng.choice(["RECEBIDA", "TRIADA", "DEVOLVIDA_CAMPO", "DESCARTADA"])}))
    for k in range(35):
        m = rng.choice(cel)
        R.append(("lab_simcards_suspensos", {"iccid": f"8955{_ri(rng, 10**14, 10**15 - 1)}1", "linha": f"(0{_ri(rng, 11, 99)}) 9{_ri(rng, 1000, 9999)}-{_ri(rng, 1000, 9999)}",
                  "operadora": m.operadora, "medidor": m.serie, "motivo": rng.choice(["INATIVIDADE", "FIM_CONTRATO", "SOLICITACAO"]),
                  "data_suspensao": d(120), "status": rng.choice(["SUSPENSO", "SUSPENSO", "REATIVADO", "CANCELADO"])}))
    for k in range(40):
        i = rng.choice(ins)
        R.append(("am_notas_afericao", {"nota": str(_ri(rng, 10_000_000, 99_999_999)), "instalacao": i.codigo,
                  "medidor": i.medidores[0].serie if i.medidores else None, "solicitante": rng.choice(["CLIENTE", "DISTRIBUIDORA", "ORGAO_REGULADOR"]),
                  "data": d(90), "status": rng.choice(["ABERTA", "MEDIDOR_RECEBIDO", "ENCERRADA"])}))
    for f in sorted({v[0] for v in MODELOS.values()}):
        R.append(("am_catalogos", {"tipo": "FABRICANTE", "valor": f, "ativo": True}))
    for irr in IRREGULARIDADES:
        R.append(("am_catalogos", {"tipo": "IRREGULARIDADE", "valor": irr, "ativo": True}))
    for t in ["Lacre plástico", "Lacre metálico", "Selo holográfico"]:
        R.append(("am_catalogos", {"tipo": "TIPO_LACRE", "valor": t, "ativo": True}))
    campo_recs = {"com_cativo_projeto": ["INSTALACAO_REMOTA", "VISTORIA"], "com_cativo_manutencao": ["TROCA_ANTENA", "TROCA_REMOTA", "REINICIO"],
           "com_cativo_programa_bt": ["INSTALACAO_CS", "TROCA_CS"], "com_cativo_outros": ["OUTRO"]}
    for rec, tipos in campo_recs.items():
        for _ in range(35 if rec != "com_cativo_outros" else 12):
            m = rng.choice(med_inst)
            i = por_id[m.instalacao_id]
            st = rng.choice(["ABERTO", "EM_CAMPO", "CONCLUIDO", "CONCLUIDO", "CANCELADO"])
            R.append((rec, {"instalacao": i.codigo, "medidor": m.serie, "ssn": m.ssn, "atendimento": at(), "tipo_servico": rng.choice(tipos),
                      "equipe": rng.choice(EQUIPES), "data_atendimento": d(60) if st == "CONCLUIDO" else None, "status": st,
                      "latitude": f"{i.lat:.5f}", "longitude": f"{i.lon:.5f}"}))
    for i in livres[:20]:
        st = rng.choice(["ABERTO", "CONCLUIDO", "CONCLUIDO"])
        R.append(("com_livre_manutencao", {"instalacao": i.codigo, "cliente": i.cliente, "medidor_principal": i.medidores[0].serie if i.medidores else None,
                  "atendimento": at(), "equipe": rng.choice(EQUIPES), "data_atendimento": d(60), "status": st, "fotos": _ri(rng, 0, 6)}))
    for k in range(30):
        st = rng.choice(["PENDENTE", "SUBSTITUIDO", "SUBSTITUIDO", "CANCELADO"])
        R.append(("com_substituicao_cs", {"cs_antigo": f"CS{_ri(rng, 100000, 999999)}", "cs_novo": f"CS{_ri(rng, 100000, 999999)}" if st == "SUBSTITUIDO" else None,
                  "agrupamento": f"AGR-{_ri(rng, 1, 60):04d}", "equipe": rng.choice(EQUIPES), "data": d(45), "status": st}))
    for k in range(18):
        R.append(("com_equipes_bot", {"id_mensageiro": str(_ri(rng, 10_000_000, 99_999_999)), "nome": _nome(rng), "equipe": EQUIPES[k % len(EQUIPES)],
                  "status": "ATIVO" if rng.random() > 0.2 else "INATIVO"}))
    for k in range(120):
        R.append(("com_logs_bot", {"sessao": f"S{k + 1:06d}", "equipe": rng.choice(EQUIPES), "comando": rng.choice(["/atendimento", "/fotos", "/consulta", "/encerrar"]),
                  "status": rng.choices(["concluido", "erro", "cancelado", "expirado"], [70, 10, 10, 10])[0], "inicio": d(30), "mensagens": _ri(rng, 2, 40)}))
    for k in range(40):
        R.append(("ger_lab_agenda", {"bancada": f"BANC-0{_ri(rng, 1, 4)}", "data": (hoje + timedelta(days=_ri(rng, -10, 30))).isoformat(),
                  "turno": rng.choice(["MANHA", "TARDE"]), "responsavel": rng.choice(["Iara Campos", "Heitor Duarte", "Analista de Laboratório"]),
                  "atividade": rng.choice(["Aferição de lote", "Calibração de bancada", "Ensaio de exatidão", "Inspeção de lacres"])}))
    sugest = [("melhoria", "Visão 360", "Exportar gráfico de consumo em imagem"), ("bug", "Programações de Nota", "Filtro de lote não limpa ao trocar município"),
              ("problema_operacional", "Console de Telemetria", "Execuções em massa demoram em horário de pico"),
              ("melhoria", "Laboratório", "Assinatura digital no laudo"), ("melhoria", "Painel", "Indicador de medidores por operadora")]
    for k, (tipo, mod, tit) in enumerate(sugest):
        R.append(("sugestoes", {"tipo": tipo, "modulo": mod, "titulo": tit, "descricao": f"{tit}. Registro de demonstração para a triagem.",
                  "impacto": rng.choice(["baixo", "medio", "alto"]), "status": rng.choice(["recebida", "em_analise", "aprovada", "concluida"]),
                  "prioridade_interna": rng.choice(["baixa", "media", "alta"]), "issue": None}))
    db.add_all(Registro(recurso=r, dados=dd) for r, dd in R)


def popular(db: Session, n_instalacoes: int = 1200, seed: int | None = None) -> dict:
    rng = random.Random(seed if seed is not None else get_settings().seed)
    hoje = date.today()
    garantir_integracoes(db)
    criar_usuarios(db, rng)
    erbs = criar_erbs(db, rng)
    insts = criar_instalacoes(db, rng, n_instalacoes, erbs, hoje)
    meds = criar_medidores(db, rng, insts, erbs, hoje)
    db.flush()
    for inst, _ in insts:
        db.refresh(inst)
    criar_trocas(db, rng, insts, hoje)
    criar_consumo(db, rng, insts, hoje)
    db.commit()
    for k in range(29, -1, -1):
        diagnostico.simular_dia(db, hoje - timedelta(days=k + 1), rng)
    db.commit()
    resumo = diagnostico.recalcular(db)
    criar_analises(db, rng, meds, insts, hoje)
    criar_registros(db, rng, insts, meds, hoje)
    db.commit()
    jobs.garantir_agendamentos(db)
    for ag in db.query(Agendamento).all():
        ag.ultima_execucao = hoje  # evita disparo imediato no primeiro start
    jobs.disparar(db, "atualizar_base_mdm", usuario="seed", sincrono=True)
    admin = db.query(Usuario).filter_by(matricula="OH0001").first()
    db.add(Notificacao(usuario_id=admin.id, titulo="Bem-vindo ao SIME", texto="Base sintética gerada. Explore os módulos pelo menu.", link="/home"))
    db.commit()
    return {**resumo, "instalacoes": len(insts), "medidores_total": len(meds), "erbs": len(erbs)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true", help="apaga e recria o banco")
    p.add_argument("--instalacoes", type=int, default=1200)
    a = p.parse_args()
    if a.reset:
        Base.metadata.drop_all(dbmod.engine)
    Base.metadata.create_all(dbmod.engine)
    db = dbmod.SessionLocal()
    try:
        if db.query(Usuario).count() and not a.reset:
            print("Banco já populado. Use --reset para recriar.")
            return
        print(popular(db, a.instalacoes))
    finally:
        db.close()


if __name__ == "__main__":
    main()
