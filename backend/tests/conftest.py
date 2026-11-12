import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="ohmnia-test-")
os.environ["OHMNIA_DATA_DIR"] = _TMP
os.environ["OHMNIA_SCHEDULER"] = "0"
os.environ["OHMNIA_DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'teste.db').as_posix()}"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core import db as dbmod  # noqa: E402
from app.core.db import Base  # noqa: E402
from app.seed import SENHA_DEMO, popular  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(dbmod.engine)
    db = dbmod.SessionLocal()
    popular(db, n_instalacoes=250, seed=7)
    db.close()
    from app.main import app
    with TestClient(app) as c:
        yield c


def _token(client, matricula):
    r = client.post("/api/auth/login", json={"matricula": matricula, "senha": SENHA_DEMO})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _token(client, "OH0001")


@pytest.fixture(scope="session")
def gestor(client):
    return _token(client, "OH0002")


@pytest.fixture(scope="session")
def analista(client):
    return _token(client, "OH0003")


@pytest.fixture(scope="session")
def campo(client):
    return _token(client, "OH0004")


@pytest.fixture(scope="session")
def consulta(client):
    return _token(client, "OH0005")


@pytest.fixture()
def db():
    s = dbmod.SessionLocal()
    yield s
    s.close()
