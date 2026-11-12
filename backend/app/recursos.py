"""Registro de recursos operacionais genéricos.

Cada recurso descreve uma tela de cadastro/consulta do sistema de referência:
campos, validações, filtros, fluxo de status e efeitos colaterais em outros
módulos. A API (`routers/recursos.py`) e a tela genérica do frontend
(`/r/[recurso]`) são dirigidas por estas definições, então todo recurso ganha
listagem com filtros, ordenação, paginação, cadastro, edição com controle de
versão, exclusão, histórico, comentários, exportação CSV, importação CSV e
alteração de status em massa.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models import Medidor, Instalacao


@dataclass
class Campo:
    nome: str
    rotulo: str
    tipo: str = "texto"  # texto | texto_longo | numero | inteiro | data | select | booleano
    obrigatorio: bool = False
    opcoes: list[str] | None = None
    padrao: str | None = None  # regex de formato
    msg_padrao: str | None = None
    min_len: int | None = None
    max_len: int | None = None
    minimo: float | None = None
    maximo: float | None = None
    ref: str | None = None  # "instalacao" | "medidor" -> deve existir na base
    lista: bool = True  # aparece na tabela
    filtro: bool = False  # vira filtro de seleção na tela
    somente_leitura: bool = False


@dataclass
class Recurso:
    chave: str
    titulo: str
    grupo: str
    permissao: str  # prefixo; ações: visualizar, criar, editar, excluir, exportar
    descricao: str
    campos: list[Campo]
    campo_status: str | None = None
    transicoes: dict[str, list[str]] | None = None
    unico: str | None = None
    somente_leitura: bool = False
    validador: Callable[[dict, dict | None], str | None] | None = field(default=None, repr=False)
    efeito: Callable[[Session, dict, dict | None, str], None] | None = field(default=None, repr=False)
    acao_atualizar: str | None = None  # job que reabastece a base (ex.: refresh do MDM)

    def campo(self, nome: str) -> Campo | None:
        return next((c for c in self.campos if c.nome == nome), None)

    def meta(self) -> dict[str, Any]:
        d = {k: v for k, v in asdict(self).items() if k not in ("validador", "efeito")}
        return d


# ----------------------------------------------------------------- validação
def validar(db: Session, rec: Recurso, dados: dict, antes: dict | None = None) -> tuple[dict, list[str]]:
    """Normaliza e valida `dados`. Retorna (dados_limpos, erros)."""
    erros: list[str] = []
    limpo: dict[str, Any] = dict(antes or {})
    for c in rec.campos:
        if c.somente_leitura and antes is not None:
            continue
        if c.nome not in dados and antes is not None:
            continue
        v = dados.get(c.nome)
        if isinstance(v, str):
            v = v.strip()
        if v in (None, ""):
            if c.obrigatorio:
                erros.append(f"{c.rotulo}: campo obrigatório.")
            limpo[c.nome] = None
            continue
        try:
            if c.tipo in ("numero",):
                v = float(str(v).replace(",", "."))
            elif c.tipo == "inteiro":
                v = int(float(str(v).replace(",", ".")))
            elif c.tipo == "data":
                v = date.fromisoformat(str(v)[:10]).isoformat()
            elif c.tipo == "booleano":
                v = str(v).lower() in ("1", "true", "sim", "s", "yes")
            else:
                v = str(v)
        except ValueError:
            erros.append(f"{c.rotulo}: valor inválido ({c.tipo}).")
            continue
        if c.opcoes and str(v) not in c.opcoes:
            erros.append(f"{c.rotulo}: use um dos valores {', '.join(c.opcoes)}.")
        if c.padrao and not re.fullmatch(c.padrao, str(v)):
            erros.append(f"{c.rotulo}: {c.msg_padrao or 'formato inválido'}.")
        if c.min_len and len(str(v)) < c.min_len:
            erros.append(f"{c.rotulo}: mínimo de {c.min_len} caracteres.")
        if c.max_len and len(str(v)) > c.max_len:
            erros.append(f"{c.rotulo}: máximo de {c.max_len} caracteres.")
        if c.minimo is not None and isinstance(v, (int, float)) and v < c.minimo:
            erros.append(f"{c.rotulo}: mínimo {c.minimo:g}.")
        if c.maximo is not None and isinstance(v, (int, float)) and v > c.maximo:
            erros.append(f"{c.rotulo}: máximo {c.maximo:g}.")
        if c.ref == "instalacao" and not db.query(Instalacao.id).filter_by(codigo=str(v)).first():
            erros.append(f"{c.rotulo}: instalação {v} não encontrada na base.")
        if c.ref == "medidor" and not db.query(Medidor.id).filter_by(serie=str(v)).first():
            erros.append(f"{c.rotulo}: medidor {v} não encontrado na base.")
        limpo[c.nome] = v
    if rec.campo_status and rec.transicoes:
        de, para = (antes or {}).get(rec.campo_status), limpo.get(rec.campo_status)
        if antes is None and para not in rec.transicoes.get(None, [para]):
            erros.append(f"Um registro novo não pode começar no status {para}.")
        elif antes is not None and de != para and para not in rec.transicoes.get(de, []):
            erros.append(f"Transição de status não permitida: {de} → {para}.")
    if not erros and rec.validador:
        msg = rec.validador(limpo, antes)
        if msg:
            erros.append(msg)
    return limpo, erros


# ---------------------------------------------------------------- utilitários
def _medidor(db: Session, serie: str | None) -> Medidor | None:
    return db.query(Medidor).filter_by(serie=serie).first() if serie else None


def _mudou(antes: dict | None, depois: dict, campo: str, valor: str) -> bool:
    return depois.get(campo) == valor and (antes or {}).get(campo) != valor


# ------------------------------------------------------- campos reaproveitados
INST =lambda obr=True: Campo("instalacao", "Instalação", obrigatorio=obr, ref="instalacao", padrao=r"\d{10}", msg_padrao="10 dígitos")  # noqa: E731
MED = lambda obr=False, nome="medidor", rot="Medidor": Campo(nome, rot, obrigatorio=obr, ref="medidor")  # noqa: E731
COORD = r"-?\d{1,3}(?:[.,]\d+)?"
NOTA = Campo("nota", "Nota de serviço", obrigatorio=True, padrao=r"\d{8,10}", msg_padrao="8 a 10 dígitos")
MUNICIPIOS = ["Vale Verde", "Porto Claro", "Serra Alta", "Rio Manso", "Campo Belo do Sul", "Nova Aurora",
              "Santa Luzia do Mar", "Pedra Azul do Norte"]
EQUIPES = [f"EQP-{n:02d}" for n in range(1, 13)]


# ------------------------------------------------------------ regras próprias
def _valida_ke(d: dict, _a: dict | None) -> str | None:
    if d.get("ke") and d.get("rtc") and d.get("rtp"):
        esperado = round(float(d["rtc"]) * float(d["rtp"]), 4)
        if abs(float(d["ke"]) - esperado) > 0.001:
            return f"KE deve ser RTC × RTP = {esperado:g}."
    return None


def _valida_campo(d: dict, _a: dict | None) -> str | None:
    if d.get("status") == "CONCLUIDO" and not (d.get("equipe") and d.get("data_atendimento")):
        return "Para concluir, informe equipe e data do atendimento."
    if bool(d.get("latitude")) != bool(d.get("longitude")):
        return "Informe latitude e longitude juntas."
    return None


def _valida_recap(d: dict, _a: dict | None) -> str | None:
    st = d.get("status")
    if st in ("aguardando_validacao", "concluida") and not d.get("atendimento_depois"):
        return "Registre o atendimento DEPOIS antes de enviar para validação."
    if st == "concluida":
        if not d.get("resultado"):
            return "Informe o resultado para concluir."
        if d["resultado"] != "substituicao_realizada" and not d.get("justificativa"):
            return "Resultado diferente de substituição realizada exige justificativa."
    if st == "em_execucao" and not d.get("atendimento_antes"):
        return "Registre o atendimento ANTES para iniciar a execução."
    return None


def _valida_programacao(d: dict, _a: dict | None) -> str | None:
    if d.get("status") == "PROGRAMADO" and not d.get("nota_dd"):
        return "Programação exige a nota DD."
    return None


def _efeito_programacao(db: Session, depois: dict, antes: dict | None, usuario: str) -> None:
    # Programação finalizada = equipe resolveu a comunicação em campo.
    if _mudou(antes, depois, "status", "FINALIZADA"):
        m = _medidor(db, depois.get("medidor"))
        if m:
            m.status_comunicacao, m.risco_falha = "COMUNICANDO", min(m.risco_falha, 20)


def _efeito_recap(db: Session, depois: dict, antes: dict | None, usuario: str) -> None:
    if _mudou(antes, depois, "status", "concluida") and depois.get("resultado") == "substituicao_realizada":
        m = _medidor(db, depois.get("medidor"))
        if m:
            m.troca_remota_recente, m.status_comunicacao = True, "COMUNICANDO"
            m.ultimo_sinal_dbm = max(m.ultimo_sinal_dbm or -110, -92.0)


def _efeito_simcard(db: Session, depois: dict, antes: dict | None, usuario: str) -> None:
    m = _medidor(db, depois.get("medidor"))
    if not m:
        return
    if _mudou(antes, depois, "status", "SUSPENSO"):
        m.status_comunicacao = "SEM COMUNICACAO"
    elif _mudou(antes, depois, "status", "REATIVADO"):
        m.status_comunicacao = "COMUNICANDO"


def _efeito_cadastral(db: Session, depois: dict, antes: dict | None, usuario: str) -> None:
    if _mudou(antes, depois, "status", "CORRIGIDO") and depois.get("campo") == "operadora":
        m = _medidor(db, depois.get("medidor"))
        if m and depois.get("valor_mdm"):
            m.operadora = depois["valor_mdm"]


ST_CAMPO = ["ABERTO", "EM_CAMPO", "CONCLUIDO", "CANCELADO"]
TR_CAMPO = {"ABERTO": ["EM_CAMPO", "CANCELADO", "CONCLUIDO"], "EM_CAMPO": ["CONCLUIDO", "CANCELADO", "ABERTO"],
          "CONCLUIDO": ["ABERTO"], "CANCELADO": ["ABERTO"], None: ST_CAMPO}


def _campo(chave: str, titulo: str, sub: str, tipo_servico: list[str]) -> Recurso:
    return Recurso(
        chave, titulo, "Comunicação de Campo", f"comunicacao-campo:{sub}",
        f"Atendimentos de comunicação em cliente cativo — {titulo.split('—')[-1].strip()}.",
        [INST(), MED(), Campo("ssn", "SSN"), Campo("atendimento", "Protocolo", padrao=r"AT\d{8}", msg_padrao="formato AT + 8 dígitos"),
         Campo("tipo_servico", "Tipo de serviço", "select", True, tipo_servico, filtro=True),
         Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True),
         Campo("data_atendimento", "Data atendimento", "data"),
         Campo("status", "Status", "select", True, ST_CAMPO, filtro=True),
         Campo("latitude", "Latitude", padrao=COORD, lista=False), Campo("longitude", "Longitude", padrao=COORD, lista=False),
         Campo("observacao", "Observação", "texto_longo", lista=False, max_len=2000)],
        campo_status="status", transicoes=TR_CAMPO, validador=_valida_campo)


RECURSOS: dict[str, Recurso] = {r.chave: r for r in [
    # --------------------------------------------------------------- Medição
    Recurso("medicao_clientes_livres", "Clientes Livres", "Medição", "medicao:clientes-livres",
            "Cadastro de medição dos clientes do mercado livre (principal e retaguarda).",
            [INST(), Campo("cliente", "Cliente", obrigatorio=True, max_len=120),
             MED(True, "medidor_principal", "Medidor principal"), MED(False, "medidor_retaguarda", "Medidor retaguarda"),
             Campo("protocolo", "Protocolo", "select", opcoes=["ABNT", "DLMS", "MODBUS"], filtro=True),
             Campo("ssn_ccee_principal", "Código SCDE", padrao=r"[A-Z]{4}\d{6}", msg_padrao="4 letras + 6 dígitos"),
             Campo("remota_principal", "Remota principal", lista=False), Campo("porta", "Porta", "inteiro", minimo=1, maximo=65535, lista=False),
             Campo("data_ultima_atualizacao", "Última atualização", "data")], unico="instalacao"),
    Recurso("medicao_base_telemedidos", "Base Telemedidos", "Medição", "medicao:base-telemedidos",
            "Espelho da base de telemedidos do MDM simulado (atualizável pela rotina).",
            [INST(), MED(True), Campo("ssn", "SSN"), Campo("grupo_leitura", "Grupo de leitura", filtro=True),
             Campo("ultima_leitura", "Última leitura", "data"),
             Campo("status_mdm", "Status MDM", "select", opcoes=["ATIVO", "SEM_LEITURA", "INATIVO"], filtro=True)],
            somente_leitura=True, acao_atualizar="atualizar_base_mdm"),
    Recurso("medicao_kes", "Constantes KE", "Medição", "medicao:kes",
            "Constantes de multiplicação (KE = RTC × RTP) das medições indiretas.",
            [INST(), MED(True), Campo("rtc", "RTC", "numero", True, minimo=1), Campo("rtp", "RTP", "numero", True, minimo=1),
             Campo("ke", "KE", "numero", True), Campo("vigencia_inicio", "Início vigência", "data", True)],
            validador=_valida_ke),
    Recurso("medicao_simplificadas", "Medições Simplificadas", "Medição", "medicao:simplificadas",
            "Migrações para medição simplificada e solicitações de retorno ao mercado cativo.",
            [Campo("id_migracao", "ID migração", obrigatorio=True, padrao=r"MIG-\d{5}", msg_padrao="formato MIG-00000"),
             INST(), Campo("cliente", "Cliente", obrigatorio=True), Campo("data_migracao", "Data migração", "data", True),
             Campo("situacao", "Situação", "select", True, ["EM_ANALISE", "APTO", "RETORNO_SOLICITADO", "RETORNADO"], filtro=True),
             Campo("observacao", "Observação", "texto_longo", lista=False)],
            campo_status="situacao", unico="id_migracao",
            transicoes={"EM_ANALISE": ["APTO", "RETORNO_SOLICITADO"], "APTO": ["RETORNO_SOLICITADO"],
                        "RETORNO_SOLICITADO": ["RETORNADO", "APTO"], "RETORNADO": [], None: ["EM_ANALISE", "APTO"]}),
    Recurso("medicao_subestacoes", "Subestações", "Medição", "medicao:subestacao",
            "Subestações e pontos de medição de fronteira.",
            [Campo("codigo", "Código", obrigatorio=True, padrao=r"SE-[A-Z]{3}", msg_padrao="formato SE-AAA"),
             Campo("nome", "Nome", obrigatorio=True), Campo("municipio", "Município", "select", True, MUNICIPIOS, filtro=True),
             Campo("tensao_kv", "Tensão (kV)", "select", True, ["13.8", "34.5", "69", "138"], filtro=True),
             Campo("medidores_fronteira", "Medidores de fronteira", "inteiro", minimo=0),
             Campo("latitude", "Latitude", padrao=COORD), Campo("longitude", "Longitude", padrao=COORD)], unico="codigo"),
    # ------------------------------------------------------------------- SMC
    Recurso("smc_agrupamentos", "Agrupamentos", "Medição Centralizada", "smc:agrupamento",
            "Concentradores (CP/CS) e seus agrupamentos de medidores.",
            [Campo("agrupamento", "Agrupamento", obrigatorio=True, padrao=r"AGR-\d{4}", msg_padrao="formato AGR-0000"),
             Campo("ssn", "SSN do concentrador"), Campo("cp", "CP"), Campo("tecnologia", "Tecnologia", "select", opcoes=["RF_MESH", "PLC", "CELULAR"], filtro=True),
             Campo("csd", "CSD"), Campo("cidade", "Cidade", "select", opcoes=MUNICIPIOS, filtro=True),
             Campo("coord_x", "Latitude", padrao=COORD, lista=False), Campo("coord_y", "Longitude", padrao=COORD, lista=False),
             Campo("porta", "Porta", "inteiro", minimo=1, maximo=65535, lista=False)], unico="agrupamento"),
    Recurso("smc_base_mdm", "Base MDM", "Medição Centralizada", "smc:base-mdm",
            "Espelho dos pontos de medição centralizada no MDM simulado.",
            [MED(True), INST(), Campo("agrupamento", "Agrupamento"), Campo("status_ponto", "Status do ponto", filtro=True),
             Campo("ultima_comunicacao", "Última comunicação", "data")], somente_leitura=True, acao_atualizar="atualizar_base_mdm"),
    Recurso("smc_controle_cadastral", "Controle Cadastral", "Medição Centralizada", "smc:controle-cadastral",
            "Divergências cadastrais entre MDM e ERP simulados.",
            [INST(), MED(), Campo("campo", "Campo divergente", "select", True, ["operadora", "modelo", "agrupamento", "endereco"], filtro=True),
             Campo("valor_mdm", "Valor no MDM"), Campo("valor_erp", "Valor no ERP"),
             Campo("status", "Status", "select", True, ["PENDENTE", "CORRIGIDO", "IGNORADO"], filtro=True)],
            campo_status="status", efeito=_efeito_cadastral,
            transicoes={"PENDENTE": ["CORRIGIDO", "IGNORADO"], "IGNORADO": ["PENDENTE"], "CORRIGIDO": [], None: ["PENDENTE"]}),
    Recurso("smc_programacoes_nota", "Programações de Nota", "Medição Centralizada", "smc:programacoes-nota",
            "Programação de notas de campo para medidores sem comunicação.",
            [INST(), Campo("nota_dd", "Nota DD", padrao=r"\d{10}", msg_padrao="10 dígitos"),
             Campo("status", "Status", "select", True, ["ABERTA", "PROGRAMADO", "NÃO PROGRAMAR", "ENCERRADO", "FINALIZADA", "INTERROMPIDA"], filtro=True),
             Campo("prioridade", "Prioridade", "select", opcoes=["0", "1", "2", "3"], filtro=True),
             Campo("lote", "Lote", "inteiro", minimo=0), Campo("municipio", "Município", "select", opcoes=MUNICIPIOS, filtro=True),
             MED(), Campo("agrupamento_id", "Agrupamento"), Campo("qtd_sem_comunicacao", "Qtd sem comunicação", "inteiro", minimo=0),
             Campo("tecnologia", "Tecnologia", "select", opcoes=["RF_MESH", "PLC", "CELULAR"], filtro=True),
             Campo("texto_equipe", "Texto para equipe", "texto_longo", lista=False), Campo("observacao", "Observação", "texto_longo", lista=False)],
            campo_status="status", validador=_valida_programacao, efeito=_efeito_programacao,
            transicoes={"ABERTA": ["PROGRAMADO", "NÃO PROGRAMAR"], "PROGRAMADO": ["FINALIZADA", "INTERROMPIDA", "ENCERRADO"],
                        "INTERROMPIDA": ["PROGRAMADO", "ENCERRADO"], "NÃO PROGRAMAR": ["ABERTA"], "FINALIZADA": [], "ENCERRADO": [],
                        None: ["ABERTA"]}),
    Recurso("smc_recapacitacao", "Recapacitação", "Medição Centralizada", "smc:recapacitacao",
            "Substituição de remotas com registro de atendimento antes/depois e validação.",
            [INST(), MED(True), Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True),
             Campo("data_programada", "Data programada", "data"),
             Campo("status", "Status", "select", True, ["programada", "em_execucao", "aguardando_validacao", "concluida", "cancelada"], filtro=True),
             Campo("atendimento_antes", "Atendimento ANTES", padrao=r"AT\d{8}", msg_padrao="formato AT + 8 dígitos"),
             Campo("atendimento_depois", "Atendimento DEPOIS", padrao=r"AT\d{8}", msg_padrao="formato AT + 8 dígitos"),
             Campo("resultado", "Resultado", "select", opcoes=["substituicao_realizada", "execucao_parcial", "manutencao_sem_substituicao", "nao_executada"], filtro=True),
             Campo("justificativa", "Justificativa", "texto_longo", lista=False, max_len=2000)],
            campo_status="status", validador=_valida_recap, efeito=_efeito_recap,
            transicoes={"programada": ["em_execucao", "cancelada"], "em_execucao": ["aguardando_validacao", "cancelada"],
                        "aguardando_validacao": ["concluida", "em_execucao"], "concluida": [], "cancelada": ["programada"],
                        None: ["programada"]}),
    # --------------------------------------------------------------- Equipes
    Recurso("equipes_notas", "Notas BT", "Equipes de Campo", "equipes:programa-bt",
            "Carteira de notas das equipes do programa de perdas em baixa tensão.",
            [NOTA, Campo("servico", "Serviço", "select", True, ["SUBSTITUICAO_CS", "RECLAMACAO", "MANUTENCAO", "IP"], filtro=True),
             INST(), Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True),
             Campo("prioridade", "Prioridade", "select", opcoes=["0", "1", "2", "3"], filtro=True),
             Campo("status", "Status", "select", True, ["PENDENTE", "EM_ROTA", "EXECUTADA", "DEVOLVIDA"], filtro=True),
             Campo("data", "Data", "data")],
            campo_status="status", unico="nota",
            transicoes={"PENDENTE": ["EM_ROTA", "DEVOLVIDA"], "EM_ROTA": ["EXECUTADA", "DEVOLVIDA", "PENDENTE"],
                        "DEVOLVIDA": ["PENDENTE"], "EXECUTADA": [], None: ["PENDENTE"]}),
    Recurso("equipes_campo", "Equipes em Campo", "Equipes de Campo", "equipes:programa-bt",
            "Situação e posição das equipes.",
            [Campo("equipe", "Equipe", "select", True, EQUIPES), Campo("encarregado", "Encarregado", obrigatorio=True),
             Campo("base", "Base", "select", True, MUNICIPIOS, filtro=True),
             Campo("situacao", "Situação", "select", True, ["DISPONIVEL", "EM_CAMPO", "INDISPONIVEL"], filtro=True),
             Campo("latitude", "Latitude", padrao=COORD, lista=False), Campo("longitude", "Longitude", padrao=COORD, lista=False)],
            unico="equipe"),
    # ------------------------------------------------------------ Laboratório
    Recurso("lab_triagem_remotas", "Triagem de Remotas", "Laboratório de Telecom", "laboratorio:triagem-remotas",
            "Triagem das remotas de comunicação devolvidas pelo campo.",
            [Campo("remota", "Remota", obrigatorio=True, padrao=r"RM\d{7}", msg_padrao="formato RM + 7 dígitos"), MED(),
             Campo("operadora", "Operadora", "select", opcoes=["Aurora Tel", "Brisa Móvel", "Celta Net"], filtro=True),
             Campo("iccid", "ICCID", padrao=r"\d{19,20}", msg_padrao="19 ou 20 dígitos"), Campo("falha_relatada", "Falha relatada"),
             Campo("diagnostico", "Diagnóstico", "select", opcoes=["OK", "DEFEITO", "SEM_SINAL", "SIM_SUSPENSO"], filtro=True),
             Campo("status", "Status", "select", True, ["RECEBIDA", "TRIADA", "DEVOLVIDA_CAMPO", "DESCARTADA"], filtro=True)],
            campo_status="status", unico="remota",
            transicoes={"RECEBIDA": ["TRIADA"], "TRIADA": ["DEVOLVIDA_CAMPO", "DESCARTADA", "RECEBIDA"], "DEVOLVIDA_CAMPO": [],
                        "DESCARTADA": [], None: ["RECEBIDA"]}),
    Recurso("lab_simcards_suspensos", "Simcards Suspensos", "Laboratório de Telecom", "laboratorio:simcards-suspensos",
            "Chips de dados suspensos e reativações.",
            [Campo("iccid", "ICCID", obrigatorio=True, padrao=r"\d{19,20}", msg_padrao="19 ou 20 dígitos"), Campo("linha", "Linha"),
             Campo("operadora", "Operadora", "select", True, ["Aurora Tel", "Brisa Móvel", "Celta Net"], filtro=True), MED(),
             Campo("motivo", "Motivo", "select", opcoes=["INATIVIDADE", "FRAUDE", "FIM_CONTRATO", "SOLICITACAO"], filtro=True),
             Campo("data_suspensao", "Data suspensão", "data"),
             Campo("status", "Status", "select", True, ["SUSPENSO", "REATIVADO", "CANCELADO"], filtro=True)],
            campo_status="status", unico="iccid", efeito=_efeito_simcard,
            transicoes={"SUSPENSO": ["REATIVADO", "CANCELADO"], "REATIVADO": ["SUSPENSO"], "CANCELADO": [], None: ["SUSPENSO"]}),
    # ---------------------------------------------------- Análise de medidores
    Recurso("am_notas_afericao", "Notas de Aferição", "Laboratório de Medidores", "analise-medidores:notas-afericao",
            "Notas que pedem aferição de medidores em laboratório.",
            [NOTA, INST(), MED(), Campo("solicitante", "Solicitante", "select", True, ["CLIENTE", "DISTRIBUIDORA", "ORGAO_REGULADOR"], filtro=True),
             Campo("data", "Data", "data", True), Campo("status", "Status", "select", True, ["ABERTA", "MEDIDOR_RECEBIDO", "ENCERRADA"], filtro=True)],
            campo_status="status", unico="nota"),
    Recurso("am_catalogos", "Configurações (catálogos)", "Laboratório de Medidores", "analise-medidores:configuracoes",
            "Catálogos usados na análise: fabricantes, irregularidades e tipos de lacre.",
            [Campo("tipo", "Tipo", "select", True, ["FABRICANTE", "IRREGULARIDADE", "TIPO_LACRE"], filtro=True),
             Campo("valor", "Valor", obrigatorio=True, max_len=80), Campo("ativo", "Ativo", "booleano")]),
    # ----------------------------------------------------- Comunicação de campo
    _campo("com_cativo_projeto", "Cliente Cativo — Projeto", "projeto", ["INSTALACAO_REMOTA", "VISTORIA"]),
    _campo("com_cativo_manutencao", "Cliente Cativo — Manutenção", "manutencao", ["TROCA_ANTENA", "TROCA_REMOTA", "REINICIO"]),
    _campo("com_cativo_programa_bt", "Cliente Cativo — Programa BT", "programa-bt", ["INSTALACAO_CS", "TROCA_CS"]),
    _campo("com_cativo_outros", "Cliente Cativo — Outros", "outros", ["OUTRO"]),
    Recurso("com_livre_manutencao", "Cliente Livre — Manutenção", "Comunicação de Campo", "comunicacao-campo:manutencao",
            "Manutenção de comunicação dos medidores de clientes livres.",
            [INST(), Campo("cliente", "Cliente"), MED(True, "medidor_principal", "Medidor principal"),
             Campo("atendimento", "Protocolo", padrao=r"AT\d{8}", msg_padrao="formato AT + 8 dígitos"),
             Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True), Campo("data_atendimento", "Data", "data"),
             Campo("status", "Status", "select", True, ST_CAMPO, filtro=True), Campo("fotos", "Fotos anexadas", "inteiro", minimo=0)],
            campo_status="status", transicoes=TR_CAMPO, validador=_valida_campo),
    Recurso("com_substituicao_cs", "Substituição de CS", "Comunicação de Campo", "comunicacao-campo:substituicao-cs",
            "Troca de concentradores secundários (CS).",
            [Campo("cs_antigo", "CS retirado", obrigatorio=True), Campo("cs_novo", "CS instalado"), Campo("agrupamento", "Agrupamento"),
             Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True), Campo("data", "Data", "data"),
             Campo("status", "Status", "select", True, ["PENDENTE", "SUBSTITUIDO", "CANCELADO"], filtro=True)],
            campo_status="status", validador=lambda d, a: "Informe o CS instalado." if d.get("status") == "SUBSTITUIDO" and not d.get("cs_novo") else None),
    Recurso("com_equipes_bot", "Cadastro de Equipes (bot)", "Comunicação de Campo", "comunicacao-campo:cadastro-equipes",
            "Usuários de campo autorizados a usar o bot de atendimento simulado.",
            [Campo("id_mensageiro", "ID no mensageiro", obrigatorio=True, padrao=r"\d{6,12}", msg_padrao="6 a 12 dígitos"),
             Campo("nome", "Nome", obrigatorio=True), Campo("equipe", "Equipe", "select", True, EQUIPES, filtro=True),
             Campo("status", "Status", "select", True, ["ATIVO", "INATIVO"], filtro=True)], unico="id_mensageiro"),
    Recurso("com_logs_bot", "Logs do Bot", "Comunicação de Campo", "comunicacao-campo:logs-bot",
            "Sessões do bot de atendimento (somente leitura).",
            [Campo("sessao", "Sessão"), Campo("equipe", "Equipe", filtro=True), Campo("comando", "Comando", filtro=True),
             Campo("status", "Status", "select", opcoes=["concluido", "erro", "cancelado", "expirado"], filtro=True),
             Campo("inicio", "Início", "data"), Campo("mensagens", "Mensagens", "inteiro")], somente_leitura=True),
    # --------------------------------------------------------------- Gestão MT
    Recurso("mt_plano_campo", "Plano de Campo", "Gestão MT", "gestao-mt:plano-campo",
            "Visitas planejadas a partir das ações recomendadas do diagnóstico.",
            [INST(), MED(True), Campo("acao_codigo", "Ação", filtro=True), Campo("prioridade", "Prioridade", "select", opcoes=["ALTA", "MEDIA", "BAIXA"], filtro=True),
             Campo("data_prevista", "Data prevista", "data"), Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True),
             Campo("status", "Status", "select", True, ["PLANEJADO", "EM_CAMPO", "EXECUTADO", "CANCELADO"], filtro=True)],
            campo_status="status"),
    Recurso("mt_controle_notas", "Controle de Notas", "Gestão MT", "gestao-mt:controle-notas",
            "Notas abertas para as instalações de média tensão.",
            [NOTA, INST(), Campo("tipo", "Tipo", "select", True, ["INSPECAO", "TROCA_MEDIDOR", "TROCA_REMOTA", "LEITURA"], filtro=True),
             Campo("abertura", "Abertura", "data", True), Campo("status", "Status", "select", True, ["ABERTA", "EM_EXECUCAO", "ENCERRADA"], filtro=True),
             Campo("resultado", "Resultado", lista=False)], campo_status="status", unico="nota"),
    Recurso("fat_triagem", "Triagem de Faturamento", "Gestão MT", "faturamento-mt:triagem",
            "Instalações MT com risco de não faturar por leitura remota no ciclo.",
            [INST(), MED(), Campo("ciclo", "Ciclo", padrao=r"\d{4}-\d{2}", msg_padrao="AAAA-MM", filtro=True),
             Campo("status_faturamento", "Status faturamento", "select", True, ["OK", "SEM COMUNICACAO", "MEDIDOR NAO RESPONDE", "INTERMITENTE"], filtro=True),
             Campo("acao", "Ação", "select", opcoes=["PREVIA_REMOTA", "LEITURA_CAMPO", "MEDIA"], filtro=True),
             Campo("status", "Status", "select", True, ["PENDENTE", "CONCLUIDO"], filtro=True)], campo_status="status"),
    Recurso("fat_agenda", "Agenda de Leitura", "Gestão MT", "faturamento-mt:triagem",
            "Calendário de leitura das instalações MT.",
            [INST(), Campo("data_leitura", "Data de leitura", "data", True), Campo("grupo", "Grupo", "select", opcoes=[f"G{n:02d}" for n in range(1, 21)], filtro=True),
             Campo("situacao", "Situação", "select", True, ["AGENDADA", "LIDA", "ATRASADA"], filtro=True)]),
    Recurso("fat_campo", "Campo (D 10:00)", "Gestão MT", "faturamento-mt:triagem",
            "Leituras de campo que precisam ocorrer até 10:00 do dia D.",
            [INST(), Campo("equipe", "Equipe", "select", opcoes=EQUIPES, filtro=True), Campo("data", "Data", "data", True),
             Campo("hora_limite", "Hora limite", padrao=r"\d{2}:\d{2}", msg_padrao="HH:MM"),
             Campo("status", "Status", "select", True, ["PENDENTE", "LIDO", "NAO_LIDO"], filtro=True)], campo_status="status"),
    Recurso("fat_exportacao", "Não enviados ao MDM", "Gestão MT", "faturamento-mt:exportacao",
            "Leituras que não seguiram para o MDM simulado e aguardam reenvio.",
            [INST(), Campo("ciclo", "Ciclo", padrao=r"\d{4}-\d{2}", msg_padrao="AAAA-MM", filtro=True),
             Campo("motivo", "Motivo", "select", opcoes=["SEM_ARQUIVO", "ARQUIVO_INCOMPLETO", "PONTO_AMBIGUO"], filtro=True),
             Campo("status", "Status", "select", True, ["FILA", "REENVIADO"], filtro=True)], campo_status="status"),
    Recurso("fat_cadastro", "Correção Cadastral MT", "Gestão MT", "faturamento-mt:cadastro",
            "Divergências de cadastro que impedem o faturamento MT.",
            [INST(), Campo("divergencia", "Divergência", "select", True, ["PONTO_STATUS_DIVERGENTE", "MEDIDOR_DIFERENTE", "KE_DIVERGENTE"], filtro=True),
             Campo("valor_mdm", "Valor MDM"), Campo("valor_erp", "Valor ERP"),
             Campo("status", "Status", "select", True, ["PENDENTE", "CORRIGIDO"], filtro=True)], campo_status="status"),
    # ----------------------------------------------------------- Gerenciamento
    Recurso("ger_lab_agenda", "Agenda do Laboratório", "Gerenciamento", "gerenciamento:lab-agenda",
            "Reserva de bancadas e atividades do laboratório.",
            [Campo("bancada", "Bancada", "select", True, ["BANC-01", "BANC-02", "BANC-03", "BANC-04"], filtro=True),
             Campo("data", "Data", "data", True), Campo("turno", "Turno", "select", True, ["MANHA", "TARDE"], filtro=True),
             Campo("responsavel", "Responsável", obrigatorio=True), Campo("atividade", "Atividade", obrigatorio=True)]),
    # -------------------------------------------------------------- Sugestões
    Recurso("sugestoes", "Sugestões e Bugs", "Sugestões", "sugestoes",
            "Canal de melhorias e problemas com triagem e comentários.",
            [Campo("tipo", "Tipo", "select", True, ["melhoria", "bug", "problema_operacional"], filtro=True),
             Campo("modulo", "Módulo", obrigatorio=True, min_len=2, max_len=40, filtro=True),
             Campo("titulo", "Título", obrigatorio=True, min_len=5, max_len=150),
             Campo("descricao", "Descrição", "texto_longo", True, min_len=10, max_len=8000, lista=False),
             Campo("impacto", "Impacto", "select", True, ["baixo", "medio", "alto"], filtro=True),
             Campo("status", "Status", "select", True, ["recebida", "em_analise", "aprovada", "em_desenvolvimento", "em_homologacao", "concluida", "rejeitada", "duplicada"], filtro=True),
             Campo("prioridade_interna", "Prioridade", "select", opcoes=["baixa", "media", "alta", "critica"], filtro=True),
             Campo("issue", "Issue vinculada", somente_leitura=True)], campo_status="status"),
]}
