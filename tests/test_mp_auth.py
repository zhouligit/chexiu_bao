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
from app.models.wechat_identity import WechatIdentity  # noqa: F401 — register metadata

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


def test_mp_login_unbound_then_bind(client):
    login = client.post("/api/v1/mp/auth/login", json={"code": "test-code-001", "client": "store"})
    assert login.status_code == 200
    body = login.json()
    assert body["code"] == 0
    assert body["data"]["bound"] is False
    assert body["data"]["token"]
    assert body["data"]["openid"]
    bind_token = body["data"]["token"]

    bind = client.post(
        "/api/v1/mp/auth/bind",
        json={"username": "admin", "password": "admin123", "client": "store"},
        headers={"Authorization": f"Bearer {bind_token}"},
    )
    assert bind.status_code == 200
    bind_body = bind.json()
    assert bind_body["code"] == 0
    assert bind_body["data"]["bound"] is True
    assert bind_body["data"]["user"]["username"] == "admin"
    access = bind_body["data"]["token"]

    me = client.get("/api/v1/mp/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "admin"
    assert me.json()["data"]["display_name"] == "管理员"

    # 再次登录应直接 bound
    login2 = client.post("/api/v1/mp/auth/login", json={"code": "test-code-001", "client": "store"})
    assert login2.json()["data"]["bound"] is True
    assert login2.json()["data"]["user"]["username"] == "admin"
