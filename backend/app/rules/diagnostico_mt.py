"""Diagnóstico de medidores (Gestão MT): risco de falha e ação recomendada final.

Reimplementação conceitual: o fluxo do sistema de referência monta um contexto
por medidor (status de faturamento, sinal, torre, estatística do modelo), simula
enlaces com torres próximas quando a falha é de comunicação com sinal fraco e
decide uma ação de campo com nível de confiança.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

RISCO_ALTO = 70.0
SINAL_BOM_DBM = -95.0
SINAL_FRACO_DBM = -101.0
SINAL_PLAUSIVEL_DBM = (-130.0, -30.0)
RAIO_BUSCA_TORRES_M = 15_000.0
TORRES_POR_OPERADORA = 2
FREQ_MHZ = 850.0
SENSIBILIDADE_MODEM_DBM = -105.0


@dataclass
class Contexto:
    medidor: str
    status_comunicacao: str
    operadora: str | None
    ultimo_sinal_dbm: float | None
    media_sinal_7d: float | None
    dias_sem_comunicar_7d: int
    modelo: str
    taxa_nr_modelo: float | None = None
    taxa_nr_parque: float | None = None
    troca_remota_recente: bool = False
    distancia_erb_m: float | None = None
    lat: float = 0
    lon: float = 0


@dataclass
class Enlace:
    erb: str
    operadora: str
    distancia_m: float
    sinal_estimado_dbm: float
    viavel: bool


@dataclass
class Acao:
    sintoma: str
    codigo: str
    titulo: str
    texto: str
    justificativa: str
    confianca: str
    dados: dict = field(default_factory=dict)


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


EXPOENTE_PERDA = 3.5  # log-distância: 2 = espaço livre; 3–4 = área urbana/suburbana


def sinal_estimado(potencia_dbm: float, dist_m: float, perda_extra_db: float = 25.0) -> float:
    """Modelo log-distância + perda de ambiente (didático, não substitui um estudo de RF)."""
    d_km = max(dist_m, 50) / 1000
    perda = 32.44 + 20 * math.log10(FREQ_MHZ) + 10 * EXPOENTE_PERDA * math.log10(d_km)
    return round(potencia_dbm - perda - perda_extra_db + 15, 1)  # +15 dBi de ganho da antena da ERB


def testar_enlaces(ctx: Contexto, erbs: list[dict]) -> list[Enlace]:
    """Avalia as torres mais próximas de cada operadora dentro do raio."""
    por_op: dict[str, list[Enlace]] = {}
    for e in erbs:
        d = distancia_m(ctx.lat, ctx.lon, e["lat"], e["lon"])
        if d > RAIO_BUSCA_TORRES_M:
            continue
        s = sinal_estimado(e.get("potencia_dbm", 46.0), d)
        por_op.setdefault(e["operadora"], []).append(Enlace(e["codigo"], e["operadora"], round(d), s, s >= SINAL_BOM_DBM))
    saida: list[Enlace] = []
    for lista in por_op.values():
        saida += sorted(lista, key=lambda x: x.distancia_m)[:TORRES_POR_OPERADORA]
    return sorted(saida, key=lambda x: -x.sinal_estimado_dbm)


def calcular_risco(ctx: Contexto) -> float:
    """Pontuação 0–100 de risco de falha nos próximos dias."""
    p = ctx.dias_sem_comunicar_7d * 8.0
    s = _sinal_ref(ctx)
    if s is not None:
        p += 20 if s <= SINAL_FRACO_DBM else 10 if s <= SINAL_BOM_DBM else 0
    if ctx.taxa_nr_modelo and ctx.taxa_nr_parque:
        razao = ctx.taxa_nr_modelo / max(ctx.taxa_nr_parque, 0.001)
        p += min(20, max(0, (razao - 1) * 10))
    if ctx.status_comunicacao in ("MEDIDOR NAO RESPONDE", "RELOGIO_CRITICO"):
        p += 15
    return round(min(100.0, p), 1)


def _sinal_ref(ctx: Contexto) -> float | None:
    for v in (ctx.media_sinal_7d, ctx.ultimo_sinal_dbm):
        if v is not None and SINAL_PLAUSIVEL_DBM[0] <= v <= SINAL_PLAUSIVEL_DBM[1]:
            return v
    return None


def precisa_simular_torres(ctx: Contexto) -> bool:
    if ctx.status_comunicacao not in ("SEM COMUNICACAO", "INTERMITENTE"):
        return False
    s = _sinal_ref(ctx)
    return s is None or s <= SINAL_BOM_DBM


def _confianca(pontos: int) -> str:
    return "ALTA" if pontos >= 3 else "MEDIA" if pontos == 2 else "BAIXA"


def decidir(ctx: Contexto, enlaces: list[Enlace] | None = None) -> Acao | None:
    enlaces = enlaces or []
    st = ctx.status_comunicacao
    s = _sinal_ref(ctx)
    if st == "COMUNICANDO":
        return None
    if st == "RELOGIO_CRITICO":
        return Acao(st, "SINCRONIZAR_RELOGIO", "Sincronizar relógio remotamente",
                    "Enviar comando de sincronismo de data/hora pelo console de telemetria.",
                    "Relógio do medidor fora da tolerância; leituras ficam com carimbo inválido.", "ALTA")
    if st == "MEDIDOR NAO RESPONDE":
        razao = (ctx.taxa_nr_modelo or 0) / max(ctx.taxa_nr_parque or 0.001, 0.001)
        if razao >= 2:
            return Acao(st, "SUBSTITUIR_MEDIDOR", "Substituir medidor (modelo com falha acima do parque)",
                        f"Programar troca do medidor {ctx.medidor} do modelo {ctx.modelo}.",
                        f"Modelo responde {razao:.1f}× menos que o parque.", _confianca(3), {"razao_modelo": round(razao, 2)})
        if ctx.troca_remota_recente:
            return Acao(st, "INSPECIONAR_CABO", "Inspecionar cabo/porta entre remota e medidor",
                        "Remota trocada recentemente e medidor não responde: verificar ligação serial.",
                        "Remota nova comunica, mas o medidor não responde à consulta.", _confianca(2))
        return Acao(st, "VISITA_TECNICA", "Visita técnica ao medidor",
                    "Verificar alimentação e display do medidor em campo.", "Sem padrão de modelo ou de troca recente.", _confianca(1))
    # falhas de comunicação
    if s is not None and s > SINAL_BOM_DBM:
        return Acao(st, "REINICIAR_REMOTA", "Reiniciar remota",
                    "Sinal bom: enviar reinício remoto e reavaliar em 24 h.", f"Sinal de referência {s:.0f} dBm é bom.", _confianca(2))
    melhor_outra = next((e for e in enlaces if e.viavel and e.operadora != ctx.operadora), None)
    melhor_mesma = next((e for e in enlaces if e.viavel and e.operadora == ctx.operadora), None)
    dados = {"torres_simuladas": [e.__dict__ for e in enlaces]}
    if melhor_mesma is None and melhor_outra is not None:
        return Acao(st, "TROCAR_OPERADORA", f"Trocar chip para {melhor_outra.operadora}",
                    f"A torre {melhor_outra.erb} ({melhor_outra.distancia_m / 1000:.1f} km) tem sinal estimado de {melhor_outra.sinal_estimado_dbm:.0f} dBm.",
                    "Nenhuma torre da operadora atual atinge sinal bom no raio de busca.", _confianca(3), dados)
    if s is not None and s <= SINAL_FRACO_DBM:
        return Acao(st, "ANTENA_EXTERNA", "Instalar antena externa de alto ganho",
                    "Sinal fraco e sem alternativa melhor de operadora.", f"Sinal de referência {s:.0f} dBm.",
                    _confianca(2 if melhor_mesma else 3), dados)
    if st == "INTERMITENTE":
        return Acao(st, "MONITORAR", "Monitorar por 7 dias", "Comunicação intermitente com sinal aceitável.",
                    "Falha não é persistente.", _confianca(1), dados)
    return Acao(st, "VERIFICAR_ANTENA", "Verificar antena e posicionamento",
                "Sinal limítrofe: verificar conector e posição da antena.", "Sinal entre -101 e -95 dBm.", _confianca(2), dados)
