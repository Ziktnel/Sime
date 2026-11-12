"""Autenticação local: senhas com bcrypt, tokens JWT HS256 e RBAC por perfil."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Usuario

# Perfil -> permissões. Formato "<modulo>:<acao>" com curinga "*".
PERFIS: dict[str, dict] = {
    "admin": {"nome": "Administrador", "permissoes": ["*"]},
    "gestor": {
        "nome": "Gestor operacional",
        "permissoes": ["*:visualizar", "*:exportar", "dashboard:*", "gestao-mt:*", "faturamento-mt:*",
                       "smc:*", "equipes:*", "medicao:*", "gerenciamento:tarefas:*", "sugestoes:*",
                       "analise-medidores:aprovar", "telemetria:*"],
    },
    "analista_lab": {
        "nome": "Analista de laboratório",
        "permissoes": ["dashboard:visualizar", "analise-medidores:*:visualizar", "analise-medidores:entrada-manual:*",
                       "analise-medidores:quarentena:*", "analise-medidores:bancada:*", "analise-medidores:notas-afericao:*",
                       "analise-medidores:configuracoes:*", "laboratorio:*", "sugestoes:criar",
                       "sugestoes:visualizar", "telemetria:visualizar"],
    },
    "operador_campo": {
        "nome": "Operador de campo",
        "permissoes": ["dashboard:visualizar", "comunicacao-campo:*", "smc:*", "equipes:*", "medicao:*:visualizar",
                       "telemetria:*", "sugestoes:criar", "sugestoes:visualizar", "gestao-mt:*:visualizar"],
    },
    # Equivale ao perfil restrito do sistema de referência: só a Visão 360.
    "consulta_360": {"nome": "Consulta Visão 360", "permissoes": ["visao-360:visualizar", "visao-360:exportar"]},
}

MAX_TENTATIVAS = 5
BLOQUEIO_MINUTOS = 15
_bearer = HTTPBearer(auto_error=False)


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=10)).decode()


def conferir_senha(senha: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), hash_.encode())
    except ValueError:
        return False


def validar_forca_senha(senha: str) -> str | None:
    if len(senha) < 8:
        return "A senha precisa ter ao menos 8 caracteres."
    if not any(c.isdigit() for c in senha) or not any(c.isalpha() for c in senha):
        return "A senha precisa ter letras e números."
    return None


def permissoes_do_perfil(perfil: str) -> list[str]:
    return PERFIS.get(perfil, {"permissoes": []})["permissoes"]


def autorizado(perfil: str, permissao: str) -> bool:
    """Confere `permissao` (ex.: 'smc:agrupamento:editar') contra os padrões do perfil."""
    return any(_casa(padrao, permissao) for padrao in permissoes_do_perfil(perfil))


def _casa(padrao: str, permissao: str) -> bool:
    p, a = padrao.split(":"), permissao.split(":")
    if p == ["*"]:
        return True
    if len(p) == 2 and p[0] == "*":  # "*:visualizar" -> qualquer permissão terminada em visualizar
        return a[-1] == p[1]
    if p[-1] == "*":  # "smc:*" -> tudo abaixo de smc
        prefixo = p[:-1]
        return len(a) > len(prefixo) and all(x in ("*", y) for x, y in zip(prefixo, a))
    return len(p) == len(a) and all(x in ("*", y) for x, y in zip(p, a))


def criar_token(usuario: Usuario) -> str:
    cfg = get_settings()
    agora = datetime.now(timezone.utc)
    payload = {"sub": usuario.matricula, "perfil": usuario.perfil, "iat": agora,
               "exp": agora + timedelta(minutes=cfg.token_minutos)}
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256")


def usuario_atual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão ausente. Faça login.")
    try:
        payload = jwt.decode(cred.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Faça login novamente.")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.")
    user = db.query(Usuario).filter_by(matricula=payload.get("sub")).first()
    if not user or not user.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo ou inexistente.")
    return user


def require_permission(permissao: str):
    def dep(user: Usuario = Depends(usuario_atual)) -> Usuario:
        if not autorizado(user.perfil, permissao):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Sem permissão: {permissao}")
        return user
    return dep
