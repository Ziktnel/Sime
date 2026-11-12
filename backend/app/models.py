"""Modelo de dados da Ohmnia (SQLite por padrão, compatível com PostgreSQL).

Entidades de domínio têm tabela própria. As listas operacionais mais simples
(cadastros de campo, programações, catálogos...) usam a tabela genérica
`registros`, descrita em `app/recursos.py`, sempre referenciando instalações e
medidores reais da base sintética.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    perfil: Mapped[str] = mapped_column(String(30))
    area: Mapped[str] = mapped_column(String(60), default="")
    senha_hash: Mapped[str] = mapped_column(String(100))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    vinculo_ativo: Mapped[bool] = mapped_column(Boolean, default=True)  # simula o RH/diretório
    tentativas_falhas: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Erb(Base):
    """Estação rádio base (torre de celular) fictícia."""
    __tablename__ = "erbs"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    operadora: Mapped[str] = mapped_column(String(30))
    tecnologia: Mapped[str] = mapped_column(String(10))
    municipio: Mapped[str] = mapped_column(String(60))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    potencia_dbm: Mapped[float] = mapped_column(Float, default=46.0)


class Instalacao(Base):
    __tablename__ = "instalacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    cliente: Mapped[str] = mapped_column(String(120))
    documento: Mapped[str] = mapped_column(String(20))  # sempre mascarado
    categoria: Mapped[str] = mapped_column(String(20))
    classe_tarifaria: Mapped[str] = mapped_column(String(30))
    classe_anterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_mudanca_classe: Mapped[date | None] = mapped_column(Date, nullable=True)
    tensao: Mapped[str] = mapped_column(String(4))  # BT / MT
    municipio: Mapped[str] = mapped_column(String(60), index=True)
    regional: Mapped[str] = mapped_column(String(30), index=True)
    bairro: Mapped[str] = mapped_column(String(60))
    endereco: Mapped[str] = mapped_column(String(160))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    situacao: Mapped[str] = mapped_column(String(20), default="LIGADA")
    data_ligacao: Mapped[date] = mapped_column(Date)
    titular_desde: Mapped[date] = mapped_column(Date)
    mmgd: Mapped[bool] = mapped_column(Boolean, default=False)
    mmgd_kwp: Mapped[float | None] = mapped_column(Float, nullable=True)
    mmgd_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    mercado: Mapped[str] = mapped_column(String(10), default="CATIVO")  # CATIVO / LIVRE
    medidores: Mapped[list["Medidor"]] = relationship(back_populates="instalacao")


class Medidor(Base):
    __tablename__ = "medidores"
    id: Mapped[int] = mapped_column(primary_key=True)
    serie: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ssn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    instalacao_id: Mapped[int | None] = mapped_column(ForeignKey("instalacoes.id"), nullable=True, index=True)
    fabricante: Mapped[str] = mapped_column(String(40))
    modelo: Mapped[str] = mapped_column(String(40))
    tecnologia: Mapped[str] = mapped_column(String(20))  # CELULAR / RF_MESH / PLC
    operadora: Mapped[str | None] = mapped_column(String(30), nullable=True)
    firmware: Mapped[str] = mapped_column(String(20))
    carga_programa: Mapped[str] = mapped_column(String(20))
    versao_hardware: Mapped[str] = mapped_column(String(10))
    erb_id: Mapped[int | None] = mapped_column(ForeignKey("erbs.id"), nullable=True)
    status_comunicacao: Mapped[str] = mapped_column(String(30), default="COMUNICANDO", index=True)
    ultimo_sinal_dbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    risco_falha: Mapped[float] = mapped_column(Float, default=0)
    situacao: Mapped[str] = mapped_column(String(20), default="INSTALADO", index=True)
    instalado_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    troca_remota_recente: Mapped[bool] = mapped_column(Boolean, default=False)
    instalacao: Mapped[Instalacao | None] = relationship(back_populates="medidores")
    erb: Mapped[Erb | None] = relationship()


class TrocaMedidor(Base):
    __tablename__ = "trocas_medidor"
    id: Mapped[int] = mapped_column(primary_key=True)
    instalacao_id: Mapped[int] = mapped_column(ForeignKey("instalacoes.id"), index=True)
    serie_retirada: Mapped[str] = mapped_column(String(20))
    serie_instalada: Mapped[str] = mapped_column(String(20))
    data: Mapped[date] = mapped_column(Date)
    motivo: Mapped[str] = mapped_column(String(60))


class ConsumoMensal(Base):
    __tablename__ = "consumo_mensal"
    __table_args__ = (UniqueConstraint("instalacao_id", "referencia"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instalacao_id: Mapped[int] = mapped_column(ForeignKey("instalacoes.id"), index=True)
    referencia: Mapped[date] = mapped_column(Date, index=True)
    kwh: Mapped[float] = mapped_column(Float)
    valor_rs: Mapped[float] = mapped_column(Float)
    adicionais_rs: Mapped[float] = mapped_column(Float, default=0)
    tipo_leitura: Mapped[str] = mapped_column(String(20), default="NORMAL")
    gerado_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    injetado_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    credito_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)


class TelemetriaDiaria(Base):
    __tablename__ = "telemetria_diaria"
    __table_args__ = (UniqueConstraint("medidor_id", "data"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    medidor_id: Mapped[int] = mapped_column(ForeignKey("medidores.id"), index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    comunicou: Mapped[bool] = mapped_column(Boolean)
    sinal_dbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    leituras_recebidas: Mapped[int] = mapped_column(Integer)
    leituras_esperadas: Mapped[int] = mapped_column(Integer, default=96)


class Analise(Base):
    """Análise laboratorial de medidor retirado de campo."""
    __tablename__ = "analises"
    id: Mapped[int] = mapped_column(primary_key=True)
    protocolo: Mapped[str] = mapped_column(String(20), unique=True)
    medidor_id: Mapped[int] = mapped_column(ForeignKey("medidores.id"), index=True)
    instalacao_codigo: Mapped[str | None] = mapped_column(String(12), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="AGUARDANDO")
    solicitante: Mapped[str] = mapped_column(String(30))  # CLIENTE / DISTRIBUIDORA / ORGAO_REGULADOR
    nota_servico: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dt_entrada: Mapped[date] = mapped_column(Date)
    dt_agendada: Mapped[date | None] = mapped_column(Date, nullable=True)
    dt_analise: Mapped[date | None] = mapped_column(Date, nullable=True)
    examinador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    aprovador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resultado: Mapped[str | None] = mapped_column(String(20), nullable=True)  # REGULAR / IRREGULAR
    irregularidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    erro_percentual: Mapped[float | None] = mapped_column(Float, nullable=True)
    lacre_numero: Mapped[str | None] = mapped_column(String(30), nullable=True)
    lacre_integro: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_laudo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quarentena: Mapped[str | None] = mapped_column(String(20), nullable=True)  # PENDENTE / VINCULADO
    versao: Mapped[int] = mapped_column(Integer, default=1)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)
    medidor: Mapped[Medidor] = relationship()


class AcaoRecomendada(Base):
    __tablename__ = "acoes_recomendadas"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataref: Mapped[date] = mapped_column(Date, index=True)
    medidor_id: Mapped[int] = mapped_column(ForeignKey("medidores.id"), index=True)
    sintoma: Mapped[str] = mapped_column(String(40))
    codigo: Mapped[str] = mapped_column(String(40), index=True)
    titulo: Mapped[str] = mapped_column(String(120))
    texto: Mapped[str] = mapped_column(Text)
    justificativa: Mapped[str] = mapped_column(Text)
    confianca: Mapped[str] = mapped_column(String(10))
    dados: Mapped[dict] = mapped_column(JSON, default=dict)
    medidor: Mapped[Medidor] = relationship()


class Registro(Base):
    """Registro genérico de um recurso operacional (ver app/recursos.py)."""
    __tablename__ = "registros"
    id: Mapped[int] = mapped_column(primary_key=True)
    recurso: Mapped[str] = mapped_column(String(50), index=True)
    dados: Mapped[dict] = mapped_column(JSON, default=dict)
    versao: Mapped[int] = mapped_column(Integer, default=1)
    criado_por: Mapped[str] = mapped_column(String(20), default="sistema")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)


class Historico(Base):
    __tablename__ = "historico"
    id: Mapped[int] = mapped_column(primary_key=True)
    entidade: Mapped[str] = mapped_column(String(50), index=True)
    entidade_id: Mapped[int] = mapped_column(Integer, index=True)
    acao: Mapped[str] = mapped_column(String(30))
    antes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    depois: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario: Mapped[str] = mapped_column(String(20))
    em: Mapped[datetime] = mapped_column(DateTime, default=agora, index=True)


class JobRun(Base):
    __tablename__ = "job_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_key: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/success/error/cancelled
    progresso: Mapped[int] = mapped_column(Integer, default=0)
    parametros: Mapped[dict] = mapped_column(JSON, default=dict)
    resultado: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log: Mapped[str] = mapped_column(Text, default="")
    disparado_por: Mapped[str] = mapped_column(String(20), default="agendador")
    iniciado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Agendamento(Base):
    __tablename__ = "agendamentos"
    job_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    horario: Mapped[str] = mapped_column(String(5))  # HH:MM diário
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultima_execucao: Mapped[date | None] = mapped_column(Date, nullable=True)


class Notificacao(Base):
    __tablename__ = "notificacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(120))
    texto: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class IntegracaoConfig(Base):
    """Comportamento de cada integração simulada (modo normal/falha/vazio/lento)."""
    __tablename__ = "integracoes"
    nome: Mapped[str] = mapped_column(String(30), primary_key=True)
    descricao: Mapped[str] = mapped_column(String(160))
    modo: Mapped[str] = mapped_column(String(10), default="normal")
    latencia_ms: Mapped[int] = mapped_column(Integer, default=150)
    chamadas: Mapped[int] = mapped_column(Integer, default=0)
    falhas: Mapped[int] = mapped_column(Integer, default=0)


class RelatorioSnapshot(Base):
    __tablename__ = "relatorios_360"
    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    instalacao_codigo: Mapped[str] = mapped_column(String(12), index=True)
    conteudo: Mapped[dict] = mapped_column(JSON)
    usuario: Mapped[str] = mapped_column(String(20))
    em: Mapped[datetime] = mapped_column(DateTime, default=agora)
