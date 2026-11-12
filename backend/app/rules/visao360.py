"""Motor de diagnóstico da Visão 360 da Instalação.

Reimplementação própria e conceitual das 14 regras identificadas no sistema de
referência (consumo, comercial, medição, micro/minigeração e vizinhança).
Cada regra recebe o dossiê da instalação e devolve um achado com severidade,
evidências e um ponto do gráfico, quando houver.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from statistics import mean, median, pstdev
from typing import Callable

PROEMINENCIA_RELATIVA = 0.2
DISTANCIA_MINIMA_PICOS = 2
SALTO_MINIMO = 0.5
MESES_TENDENCIA = 3
FAIXA_ESTAVEL = 0.10
FAIXA_MODERADA = 0.20
PRODUTIVIDADE_KWH_KWP_MES = 120.0  # referência didática para geração solar
GERACAO_MINIMA_ESPERADA = 0.70
HORAS_SOL_MAX_DIA = 7.0
VIZINHANCA_LIMIAR = 0.40


@dataclass
class Mes:
    referencia: date
    kwh: float
    valor_rs: float
    adicionais_rs: float = 0
    tipo_leitura: str = "NORMAL"
    gerado_kwh: float | None = None
    injetado_kwh: float | None = None
    credito_kwh: float | None = None


@dataclass
class Dossie:
    codigo: str
    categoria: str
    classe_tarifaria: str
    classe_anterior: str | None
    data_mudanca_classe: date | None
    titular_desde: date
    mmgd: bool
    mmgd_kwp: float | None
    mmgd_desde: date | None
    serie: list[Mes]
    trocas: list[dict] = field(default_factory=list)
    mediana_vizinhanca_kwh: float | None = None
    mediana_injecao_perfil: float | None = None


@dataclass
class Achado:
    codigo: str
    titulo: str
    severidade: str  # info | atencao | critico
    descricao: str
    evidencias: list[str]
    referencia: str | None = None


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def _ref(d: date) -> str:
    return d.strftime("%m/%Y")


def detectar_picos(valores: list[float], proeminencia: float = PROEMINENCIA_RELATIVA,
                   distancia: int = DISTANCIA_MINIMA_PICOS) -> list[int]:
    """Picos locais da série normalizada 0..1 com proeminência mínima.

    Proeminência = altura do pico menos o maior dos mínimos à esquerda e à
    direita até encontrar um valor maior que o pico (definição topográfica).
    """
    if len(valores) < 3:
        return []
    lo, hi = min(valores), max(valores)
    if hi == lo:
        return []
    n = [(v - lo) / (hi - lo) for v in valores]
    candidatos = []
    for i in range(1, len(n) - 1):
        if n[i] > n[i - 1] and n[i] >= n[i + 1]:
            esq = n[i]
            for j in range(i - 1, -1, -1):
                if n[j] > n[i]:
                    break
                esq = min(esq, n[j])
            dir_ = n[i]
            for j in range(i + 1, len(n)):
                if n[j] > n[i]:
                    break
                dir_ = min(dir_, n[j])
            if n[i] - max(esq, dir_) >= proeminencia:
                candidatos.append(i)
    # distância mínima: mantém o maior pico de cada vizinhança
    escolhidos: list[int] = []
    for i in sorted(candidatos, key=lambda k: -n[k]):
        if all(abs(i - j) >= distancia for j in escolhidos):
            escolhidos.append(i)
    return sorted(escolhidos)


# ---------------------------------------------------------------- consumo
def con_001(d: Dossie) -> Achado | None:
    kwh = [m.kwh for m in d.serie]
    picos = detectar_picos(kwh)
    if not picos:
        return None
    media = mean(kwh)
    relevantes = [i for i in picos if kwh[i] > media * 1.3]
    if not relevantes:
        return None
    return Achado("CON-001", "Pico significativo de consumo", "atencao",
                  f"{len(relevantes)} pico(s) acima de 130% da média do período.",
                  [f"{_ref(d.serie[i].referencia)}: {kwh[i]:.0f} kWh (média {media:.0f})" for i in relevantes],
                  _ref(d.serie[relevantes[-1]].referencia))


def con_002(d: Dossie) -> Achado | None:
    ev = []
    for a, b in zip(d.serie, d.serie[1:]):
        if a.kwh > 0 and abs(b.kwh - a.kwh) / a.kwh >= SALTO_MINIMO:
            ev.append(f"{_ref(a.referencia)}→{_ref(b.referencia)}: {a.kwh:.0f} → {b.kwh:.0f} kWh ({_pct((b.kwh - a.kwh) / a.kwh)})")
    if not ev:
        return None
    return Achado("CON-002", "Salto de consumo ou valor", "atencao" if len(ev) < 3 else "critico",
                  f"{len(ev)} variação(ões) mês a mês de pelo menos {_pct(SALTO_MINIMO)}.", ev[-5:])


def con_003(d: Dossie) -> Achado | None:
    kwh = [m.kwh for m in d.serie[-12:]]
    if len(kwh) < 6 or mean(kwh) == 0:
        return None
    cv = pstdev(kwh) / mean(kwh)
    faixa = "estável" if cv <= FAIXA_ESTAVEL else "moderada" if cv <= FAIXA_MODERADA else "instável"
    sev = "info" if faixa != "instável" else "atencao"
    return Achado("CON-003", "Faixa de estabilidade do consumo", sev,
                  f"Consumo {faixa} nos últimos 12 meses (coeficiente de variação {_pct(cv)}).",
                  [f"Média {mean(kwh):.0f} kWh, desvio {pstdev(kwh):.0f} kWh"])


def con_004(d: Dossie) -> Achado | None:
    idx = next((i for i, m in enumerate(d.serie) if m.referencia >= d.titular_desde), None)
    if idx is None or idx < MESES_TENDENCIA or idx + MESES_TENDENCIA > len(d.serie):
        return None
    antes = mean(m.kwh for m in d.serie[idx - MESES_TENDENCIA:idx])
    depois = mean(m.kwh for m in d.serie[idx:idx + MESES_TENDENCIA])
    if antes == 0 or abs(depois - antes) / antes < 0.3:
        return None
    return Achado("CON-004", "Mudança de consumo próxima à troca de titularidade", "atencao",
                  f"Média de {MESES_TENDENCIA} meses mudou {_pct((depois - antes) / antes)} após a troca de titular.",
                  [f"Antes: {antes:.0f} kWh", f"Depois: {depois:.0f} kWh", f"Titular desde {d.titular_desde:%d/%m/%Y}"],
                  _ref(d.titular_desde))


# --------------------------------------------------------------- comercial
def com_001(d: Dossie) -> Achado | None:
    if not d.classe_anterior or not d.data_mudanca_classe:
        return None
    return Achado("COM-001", "Mudança de categoria tarifária", "info",
                  f"Classe alterada de {d.classe_anterior} para {d.classe_tarifaria}.",
                  [f"Em {d.data_mudanca_classe:%d/%m/%Y}"], _ref(d.data_mudanca_classe))


def com_002(d: Dossie) -> Achado | None:
    ev = [f"{_ref(m.referencia)}: R$ {m.adicionais_rs:.2f} de adicionais sobre R$ {m.valor_rs:.2f}"
          for m in d.serie if m.valor_rs > 0 and m.adicionais_rs / m.valor_rs >= 0.15]
    if not ev:
        return None
    return Achado("COM-002", "Valores adicionais relevantes", "atencao",
                  f"{len(ev)} fatura(s) com adicionais acima de 15% do valor.", ev[-5:])


# ----------------------------------------------------------------- medição
def med_001(d: Dossie) -> Achado | None:
    ultimos = d.serie[-6:]
    criticos = [m for m in ultimos if m.tipo_leitura in ("MEDIA", "ESTIMADA", "IMPEDIMENTO")]
    if len(criticos) < 2:
        return None
    return Achado("MED-001", "Tipo de leitura crítico", "critico" if len(criticos) >= 4 else "atencao",
                  f"{len(criticos)} dos últimos 6 faturamentos sem leitura real.",
                  [f"{_ref(m.referencia)}: {m.tipo_leitura}" for m in criticos])


def med_002(d: Dossie) -> Achado | None:
    if not d.trocas:
        return None
    return Achado("MED-002", "Troca ou retirada de medidor", "info",
                  f"{len(d.trocas)} troca(s) de medidor registrada(s).",
                  [f"{t['data']}: {t['serie_retirada']} → {t['serie_instalada']} ({t['motivo']})" for t in d.trocas],
                  d.trocas[-1]["data"][3:] if d.trocas else None)


# --------------------------------------------------------------------- MMGD
def _antes_depois_mmgd(d: Dossie) -> tuple[list[Mes], list[Mes]]:
    if not d.mmgd_desde:
        return [], d.serie
    return [m for m in d.serie if m.referencia < d.mmgd_desde], [m for m in d.serie if m.referencia >= d.mmgd_desde]


def gd_001(d: Dossie) -> Achado | None:
    antes, depois = _antes_depois_mmgd(d)
    if not d.mmgd or len(antes) < 3 or len(depois) < 3:
        return None
    a, b = mean(m.kwh for m in antes[-6:]), mean(m.kwh for m in depois[:6])
    if a == 0 or (a - b) / a < 0.3:
        return None
    return Achado("GD-001", "Redução de consumo após MMGD", "info",
                  f"Consumo faturado caiu {_pct((a - b) / a)} após a conexão da geração.",
                  [f"Antes: {a:.0f} kWh", f"Depois: {b:.0f} kWh"], _ref(d.mmgd_desde))


def gd_002(d: Dossie) -> Achado | None:
    _, depois = _antes_depois_mmgd(d)
    gerados = [m for m in depois if m.gerado_kwh is not None]
    if not d.mmgd or not d.mmgd_kwp or len(gerados) < 3:
        return None
    esperado = d.mmgd_kwp * PRODUTIVIDADE_KWH_KWP_MES
    real = mean(m.gerado_kwh for m in gerados[-6:])
    if real >= esperado * GERACAO_MINIMA_ESPERADA:
        return None
    return Achado("GD-002", "Geração aquém da esperada", "atencao",
                  f"Geração média de {real:.0f} kWh/mês, {_pct(real / esperado)} do esperado para {d.mmgd_kwp:g} kWp.",
                  [f"Esperado ≈ {esperado:.0f} kWh/mês ({PRODUTIVIDADE_KWH_KWP_MES:g} kWh/kWp)"])


def gd_003(d: Dossie) -> Achado | None:
    cred = [m for m in d.serie if m.credito_kwh is not None]
    if len(cred) < 6:
        return None
    a, b = mean(m.credito_kwh for m in cred[-6:-3]), mean(m.credito_kwh for m in cred[-3:])
    if a <= 0 or (a - b) / a < 0.4:
        return None
    return Achado("GD-003", "Queda do crédito MMGD utilizado", "atencao",
                  f"Crédito utilizado caiu {_pct((a - b) / a)} no último trimestre.", [f"{a:.0f} → {b:.0f} kWh"])


def gd_004(d: Dossie) -> Achado | None:
    if not d.mmgd or not d.mmgd_kwp:
        return None
    maximo = d.mmgd_kwp * HORAS_SOL_MAX_DIA * 31
    ev = [f"{_ref(m.referencia)}: {m.injetado_kwh:.0f} kWh (máx. físico {maximo:.0f})"
          for m in d.serie if m.injetado_kwh and m.injetado_kwh > maximo]
    if not ev:
        return None
    return Achado("GD-004", "Energia injetada acima do máximo físico", "critico",
                  "Injeção maior do que a potência instalada permite — possível erro de cadastro ou medição.", ev)


def gd_005(d: Dossie) -> Achado | None:
    inj = [m.injetado_kwh for m in d.serie[-6:] if m.injetado_kwh is not None]
    if not d.mmgd or not inj or not d.mediana_injecao_perfil or not d.mmgd_kwp:
        return None
    por_kwp = mean(inj) / d.mmgd_kwp
    if por_kwp >= d.mediana_injecao_perfil * 0.5:
        return None
    return Achado("GD-005", "Injeção abaixo das instalações de perfil semelhante", "atencao",
                  f"{por_kwp:.0f} kWh/kWp contra mediana de {d.mediana_injecao_perfil:.0f} kWh/kWp do perfil.", [])


def viz_001(d: Dossie) -> Achado | None:
    if not d.mediana_vizinhanca_kwh or len(d.serie) < 6:
        return None
    media = mean(m.kwh for m in d.serie[-6:])
    razao = media / d.mediana_vizinhanca_kwh
    if razao >= VIZINHANCA_LIMIAR and razao <= 1 / VIZINHANCA_LIMIAR:
        return None
    return Achado("VIZ-001", "Consumo destoante da vizinhança", "critico" if razao < VIZINHANCA_LIMIAR else "atencao",
                  f"Consumo médio é {_pct(razao)} da mediana de instalações semelhantes do bairro.",
                  [f"Instalação: {media:.0f} kWh", f"Mediana vizinhança: {d.mediana_vizinhanca_kwh:.0f} kWh"])


REGRAS: list[tuple[str, str, Callable[[Dossie], Achado | None]]] = [
    ("CON-001", "Consumo", con_001), ("CON-002", "Consumo", con_002), ("CON-003", "Consumo", con_003),
    ("CON-004", "Consumo", con_004), ("COM-001", "Comercial", com_001), ("COM-002", "Comercial", com_002),
    ("MED-001", "Medição", med_001), ("MED-002", "Medição", med_002), ("GD-001", "MMGD", gd_001),
    ("GD-002", "MMGD", gd_002), ("GD-003", "MMGD", gd_003), ("GD-004", "MMGD", gd_004),
    ("GD-005", "MMGD", gd_005), ("VIZ-001", "Vizinhança", viz_001),
]
PESO = {"info": 0, "atencao": 2, "critico": 5}


def diagnosticar(d: Dossie) -> dict:
    achados = []
    for codigo, grupo, regra in REGRAS:
        a = regra(d)
        if a:
            achados.append({**asdict(a), "grupo": grupo})
    pontos = sum(PESO[a["severidade"]] for a in achados)
    nivel = "ALTO" if pontos >= 8 else "MEDIO" if pontos >= 3 else "BAIXO"
    return {"achados": achados, "pontuacao": pontos, "nivel_suspeita": nivel,
            "regras_avaliadas": len(REGRAS),
            "mediana_kwh": median([m.kwh for m in d.serie]) if d.serie else None}
