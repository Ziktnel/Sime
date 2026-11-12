"""Camada de integrações simuladas.

No sistema de referência estes serviços eram externos (ERP, MDM, head-end de
telemetria, data lake, câmara de comercialização, bot de mensagens, issue
tracker). Aqui cada um é um serviço local cujo comportamento é configurável
em tempo de execução pela tela "Integrações simuladas":

- normal : responde com dados calculados da base sintética
- vazio  : responde com sucesso, mas sem registros
- falha  : levanta IntegracaoIndisponivel (a API devolve 502)
- lento  : responde normalmente após latência alta
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.models import IntegracaoConfig

INTEGRACOES = {
    "erp": "ERP simulado (notas de serviço, ordens de campo)",
    "mdm": "Sistema de gestão de medição (MDM) simulado — base de telemedidos e cadastros",
    "headend": "Head-end de telemetria simulado — comandos remotos e leituras",
    "datalake": "Data lake simulado — histórico de consumo e comissionamento",
    "ccee": "Câmara de comercialização simulada — curvas de medição SCDE",
    "bot": "Bot de mensagens simulado — atendimentos de equipes em campo",
    "diretorio": "Diretório corporativo simulado — vínculo ativo dos usuários",
    "issues": "Issue tracker simulado — encaminhamento de sugestões",
}


class IntegracaoIndisponivel(RuntimeError):
    def __init__(self, nome: str) -> None:
        super().__init__(f"Integração '{nome}' indisponível (simulação de falha).")
        self.nome = nome


def garantir_integracoes(db: Session) -> None:
    for nome, descricao in INTEGRACOES.items():
        if not db.get(IntegracaoConfig, nome):
            db.add(IntegracaoConfig(nome=nome, descricao=descricao))
    db.commit()


def chamar(db: Session, nome: str) -> str:
    """Registra a chamada e aplica o modo configurado. Retorna o modo efetivo."""
    cfg = db.get(IntegracaoConfig, nome)
    if cfg is None:
        garantir_integracoes(db)
        cfg = db.get(IntegracaoConfig, nome)
    cfg.chamadas += 1
    modo = cfg.modo
    if modo == "lento":
        time.sleep(min(cfg.latencia_ms, 5000) / 1000)
    if modo == "falha":
        cfg.falhas += 1
        db.commit()
        raise IntegracaoIndisponivel(nome)
    db.commit()
    return modo
