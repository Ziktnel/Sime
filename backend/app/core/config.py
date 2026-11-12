"""Configuração por ambiente. Nenhum segredo fica no código-fonte.

Variáveis aceitas (todas opcionais):
- OHMNIA_DATABASE_URL  (padrão: sqlite em backend/data/ohmnia.db)
- OHMNIA_JWT_SECRET    (padrão: gerado na primeira execução e salvo em backend/data/.jwt_secret)
- OHMNIA_TOKEN_MINUTOS (padrão: 480)
- OHMNIA_SEED          (semente dos dados sintéticos, padrão: 2026)
- OHMNIA_SCHEDULER     ("0" desliga o agendador de rotinas)
"""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("OHMNIA_DATA_DIR", BACKEND_DIR / "data"))


class Settings:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.database_url = os.getenv("OHMNIA_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'ohmnia.db').as_posix()}")
        self.jwt_secret = os.getenv("OHMNIA_JWT_SECRET") or self._segredo_local()
        self.token_minutos = int(os.getenv("OHMNIA_TOKEN_MINUTOS", "480"))
        self.seed = int(os.getenv("OHMNIA_SEED", "2026"))
        self.scheduler = os.getenv("OHMNIA_SCHEDULER", "1") != "0"
        self.cors_origins = os.getenv("OHMNIA_CORS", "http://localhost:3000").split(",")

    @staticmethod
    def _segredo_local() -> str:
        arquivo = DATA_DIR / ".jwt_secret"
        if not arquivo.exists():
            arquivo.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        return arquivo.read_text(encoding="utf-8").strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
