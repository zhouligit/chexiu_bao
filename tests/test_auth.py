import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.store import Store
from app.models.rbac import Permission, StoreRole  # noqa: F401
from app.models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def seed_test_data(db):
    from app.services.role_bootstrap import RoleBootstrap

    store = Store(id=1, name="演示汽修店", code="demo", phone="400-000-0000", address="演示地址")
    db.add(store)
    db.flush()
    roles = RoleBootstrap.ensure_store_roles(db, 1)
    user = User(
        id=1,
        store_id=1,
        username="admin",
        password_hash=hash_password("admin123"),
        name="管理员",
        role="owner",
        role_id=roles["owner"].id,
    )
    db.add(user)
    db.commit()


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_test_data(db)
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]
    assert body["data"]["user"]["username"] == "admin"


def test_login_failure(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 401


def test_receptionist_cannot_manage_users(client):
    from app.services.role_bootstrap import RoleBootstrap

    db = TestingSessionLocal()
    roles = RoleBootstrap.ensure_store_roles(db, 1)
    receptionist = User(
        id=2,
        store_id=1,
        username="qiantai_test",
        password_hash=hash_password("test123456"),
        name="前台测试",
        role="receptionist",
        role_id=roles["receptionist"].id,
    )
    db.add(receptionist)
    db.commit()
    receptionist_role_id = roles["receptionist"].id
    db.close()

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "qiantai_test", "password": "test123456"},
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    access = client.get("/api/v1/users/access", headers=headers)
    assert access.json()["code"] == 0
    data = access.json()["data"]
    assert data["can_open_management"] is False
    assert data["can_create"] is False
    assert data["role_slug"] == "receptionist"

    create = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "new_user_x",
            "password": "test123456",
            "name": "新用户",
            "role_id": receptionist_role_id,
        },
    )
    assert create.json()["code"] == 403
