import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.db import create_all, init_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    from app.config import get_settings

    get_settings.cache_clear()
    import app.db as db_mod

    db_mod._engine = None
    db_mod._SessionLocal = None
    init_engine(f"sqlite:///{tmp_path}/test.db")
    create_all()

    from app.main import app

    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()
