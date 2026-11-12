"""Testes unitários das regras de negócio (sem banco)."""
from datetime import date

from app.core.security import autorizado
from app.rules import diagnostico_mt as mt
from app.rules import visao360 as v


def _serie(valores, inicio=date(2025, 1, 1), **extra):
    out = []
    for k, kwh in enumerate(valores):
        ref = date(inicio.year + (inicio.month - 1 + k) // 12, (inicio.month - 1 + k) % 12 + 1, 1)
        out.append(v.Mes(ref, kwh, kwh * 0.9, **{c: (f(k) if callable(f) else f) for c, f in extra.items()}))
    return out


def _dossie(serie, **kw):
    base = dict(codigo="4000000001", categoria="RESIDENCIAL", classe_tarifaria="B1", classe_anterior=None, data_mudanca_classe=None,
                titular_desde=date(2010, 1, 1), mmgd=False, mmgd_kwp=None, mmgd_desde=None, serie=serie)
    base.update(kw)
    return v.Dossie(**base)


# ------------------------------------------------------------ Visão 360
def test_detectar_picos_respeita_proeminencia():
    assert v.detectar_picos([1, 1, 1, 10, 1, 1, 1]) == [3]
    assert v.detectar_picos([5, 5.1, 5, 5.05, 5]) != []  # normalizado, pequenas oscilações relativas contam
    assert v.detectar_picos([1, 2]) == []
    assert v.detectar_picos([3, 3, 3]) == []


def test_con_002_salto_de_consumo():
    a = v.con_002(_dossie(_serie([100, 100, 160, 160])))
    assert a and a.codigo == "CON-002"
    assert v.con_002(_dossie(_serie([100, 120, 140, 150]))) is None


def test_con_003_faixas_de_estabilidade():
    assert "estável" in v.con_003(_dossie(_serie([100] * 12))).descricao
    assert v.con_003(_dossie(_serie([50, 150] * 6))).severidade == "atencao"


def test_med_001_leituras_nao_reais():
    serie = _serie([100] * 6, tipo_leitura=lambda k: "MEDIA" if k >= 2 else "NORMAL")
    assert v.med_001(_dossie(serie)).severidade == "critico"


def test_gd_004_injecao_acima_do_maximo_fisico():
    serie = _serie([100] * 3, injetado_kwh=5000.0)
    a = v.gd_004(_dossie(serie, mmgd=True, mmgd_kwp=5.0, mmgd_desde=date(2025, 1, 1)))
    assert a and a.severidade == "critico"


def test_viz_001_vizinhanca():
    assert v.viz_001(_dossie(_serie([30] * 6), mediana_vizinhanca_kwh=200)).severidade == "critico"
    assert v.viz_001(_dossie(_serie([180] * 6), mediana_vizinhanca_kwh=200)) is None


def test_diagnosticar_pontua_e_classifica():
    d = _dossie(_serie([100, 100, 300, 100, 30, 30, 30, 30], tipo_leitura=lambda k: "ESTIMADA" if k > 3 else "NORMAL"),
                mediana_vizinhanca_kwh=400)
    r = v.diagnosticar(d)
    assert r["regras_avaliadas"] == 14
    assert r["nivel_suspeita"] == "ALTO"
    assert {"CON-002", "MED-001", "VIZ-001"} <= {a["codigo"] for a in r["achados"]}


# ------------------------------------------------------------ Diagnóstico MT
def _ctx(**kw):
    base = dict(medidor="X", status_comunicacao="SEM COMUNICACAO", operadora="Aurora Tel", ultimo_sinal_dbm=-110.0,
                media_sinal_7d=None, dias_sem_comunicar_7d=7, modelo="M", lat=-20.0, lon=-43.0)
    base.update(kw)
    return mt.Contexto(**base)


def test_sinal_bom_reinicia_remota():
    assert mt.decidir(_ctx(ultimo_sinal_dbm=-80.0)).codigo == "REINICIAR_REMOTA"


def test_sinal_fraco_sem_alternativa_pede_antena():
    assert mt.decidir(_ctx(), []).codigo == "ANTENA_EXTERNA"


def test_troca_de_operadora_quando_so_outra_tem_sinal():
    enlaces = [mt.Enlace("E1", "Brisa Móvel", 900, -80.0, True), mt.Enlace("E2", "Aurora Tel", 9000, -112.0, False)]
    a = mt.decidir(_ctx(), enlaces)
    assert a.codigo == "TROCAR_OPERADORA" and a.confianca == "ALTA"


def test_modelo_com_falha_acima_do_parque_substitui():
    a = mt.decidir(_ctx(status_comunicacao="MEDIDOR NAO RESPONDE", taxa_nr_modelo=0.2, taxa_nr_parque=0.05))
    assert a.codigo == "SUBSTITUIR_MEDIDOR"


def test_relogio_e_comunicando():
    assert mt.decidir(_ctx(status_comunicacao="RELOGIO_CRITICO")).codigo == "SINCRONIZAR_RELOGIO"
    assert mt.decidir(_ctx(status_comunicacao="COMUNICANDO")) is None


def test_sinal_implausivel_e_ignorado():
    assert mt._sinal_ref(_ctx(ultimo_sinal_dbm=-200.0)) is None


def test_risco_limitado_a_100_e_cresce_com_falhas():
    assert mt.calcular_risco(_ctx(dias_sem_comunicar_7d=7, status_comunicacao="MEDIDOR NAO RESPONDE", taxa_nr_modelo=1, taxa_nr_parque=0.01)) == 100
    assert mt.calcular_risco(_ctx(dias_sem_comunicar_7d=0, ultimo_sinal_dbm=-70.0)) == 0


def test_enlace_respeita_raio_e_limite_por_operadora():
    erbs = [{"codigo": f"E{k}", "operadora": "A", "lat": -20.0 + k * 0.01, "lon": -43.0} for k in range(5)]
    erbs.append({"codigo": "LONGE", "operadora": "B", "lat": -21.0, "lon": -43.0})
    r = mt.testar_enlaces(_ctx(), erbs)
    assert len(r) == mt.TORRES_POR_OPERADORA and all(e.erb != "LONGE" for e in r)


# ------------------------------------------------------------------ RBAC
def test_rbac_curingas():
    assert autorizado("admin", "qualquer:coisa")
    assert autorizado("gestor", "smc:agrupamento:editar")
    assert autorizado("gestor", "laboratorio:simcards-suspensos:visualizar")
    assert not autorizado("gestor", "laboratorio:simcards-suspensos:excluir")
    assert autorizado("operador_campo", "medicao:kes:visualizar")
    assert not autorizado("operador_campo", "medicao:kes:editar")
    assert not autorizado("consulta_360", "dashboard:visualizar")
    assert autorizado("analista_lab", "analise-medidores:indicadores:visualizar")
    assert not autorizado("analista_lab", "analise-medidores:aprovar")  # segregação de função
    assert autorizado("consulta_360", "visao-360:visualizar")
