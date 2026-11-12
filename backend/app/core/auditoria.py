from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Historico, Notificacao, Usuario
from app.core.security import autorizado


def registrar(db: Session, entidade: str, entidade_id: int, acao: str, usuario: str,
              antes: dict | None = None, depois: dict | None = None, texto: str | None = None) -> None:
    db.add(Historico(entidade=entidade, entidade_id=entidade_id, acao=acao, usuario=usuario,
                     antes=antes, depois=depois, texto=texto))


def diff(antes: dict, depois: dict) -> tuple[dict, dict]:
    chaves = {k for k in set(antes) | set(depois) if antes.get(k) != depois.get(k)}
    return {k: antes.get(k) for k in chaves}, {k: depois.get(k) for k in chaves}


def notificar_permissao(db: Session, permissao: str, titulo: str, texto: str, link: str | None = None) -> int:
    """Envia notificação para todo usuário ativo cujo perfil tem `permissao` (sino por permissão)."""
    n = 0
    for u in db.query(Usuario).filter_by(ativo=True).all():
        if autorizado(u.perfil, permissao):
            db.add(Notificacao(usuario_id=u.id, titulo=titulo, texto=texto, link=link))
            n += 1
    return n
