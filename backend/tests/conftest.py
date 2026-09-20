import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.database.session import get_db
from app.database.seed_data import seed_database
from app.core.config import settings
from app.main import app

# In-memory SQLite for isolated tests
TEST_DB_URL = "sqlite:///./test_landslide.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    # Original regression tests exercise legacy single-operator mode.
    # test_role_access explicitly enables the production-default role guard.
    monkeypatch.setenv("RBAC_ENABLED", "false")
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("OPERATIONS_API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_COOKIE_SECURE", raising=False)
    monkeypatch.setattr(settings, "OPERATIONS_API_KEY", "")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("./test_landslide.db"):
        try:
            os.remove("./test_landslide.db")
        except PermissionError:
            pass

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
