import os
import tempfile

# configure BEFORE importing the app (settings + engine are module-level)
_tmp = tempfile.mkdtemp(prefix="ldna-test-")
os.environ["LEARNDNA_DATABASE_URL"] = os.environ.get("LEARNDNA_TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["LEARNDNA_LOCAL_STORAGE_DIR"] = f"{_tmp}/uploads"
os.environ["LEARNDNA_TASK_BACKEND"] = "inline"
os.environ["LEARNDNA_ENV"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import DEMO_PASSWORD, seed  # noqa: E402


@pytest.fixture(scope="session")
def seeded():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        info = seed(db)
        other = seed(db, process=False, email_suffix="-x")  # second tenant for isolation tests
    return {"main": info, "other": other}


@pytest.fixture(scope="session")
def client(seeded):
    return TestClient(app)


def token(client, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def teacher(client):
    return token(client, "ogretmen@demo.bcn")
