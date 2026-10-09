from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.appointment import Appointment  # noqa: F401
from app.models.customer import Customer, Vehicle
from app.models.store import Store
from app.models.user import User
from app.models.work_order import WorkOrder  # noqa: F401

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def seed(db):
    store = Store(id=1, name="演示汽修店", code="demo")
    user = User(
        id=1,
        store_id=1,
        username="admin",
        password_hash=hash_password("admin123"),
        name="管理员",
        role="owner",
    )
    customer = Customer(id=1, store_id=1, name="张三", phone="13800001111")
    vehicle = Vehicle(id=1, store_id=1, customer_id=1, plate_number="粤B12345")
    db.add_all([store, user, customer, vehicle])
    db.commit()


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed(db)
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _token(client: TestClient) -> str:
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.json()["code"] == 0
    return res.json()["data"]["access_token"]


def test_appointment_flow(client):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    created = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "contact_name": "张三",
            "contact_phone": "13800001111",
            "plate_number": "粤B12345",
            "scheduled_start": start,
            "customer_id": 1,
            "vehicle_id": 1,
            "remark": "更换机油",
            "source": "mp_store",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "pending"
    appt_id = body["data"]["id"]

    listed = client.get("/api/v1/appointments?status=pending", headers=headers)
    assert listed.json()["data"]["total"] >= 1

    confirmed = client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=headers)
    assert confirmed.json()["data"]["status"] == "confirmed"

    arrived = client.post(f"/api/v1/appointments/{appt_id}/arrive", headers=headers)
    assert arrived.json()["data"]["status"] == "arrived"

    converted = client.post(f"/api/v1/appointments/{appt_id}/convert", headers=headers)
    data = converted.json()["data"]
    assert data["status"] == "converted"
    assert data["work_order_id"]


def test_appointment_cancel(client):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    created = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "contact_name": "李四",
            "contact_phone": "13900002222",
            "plate_number": "粤B99999",
            "scheduled_start": start,
        },
    )
    appt_id = created.json()["data"]["id"]
    cancelled = client.post(
        f"/api/v1/appointments/{appt_id}/cancel",
        headers=headers,
        json={"remark": "客户改期"},
    )
    assert cancelled.json()["data"]["status"] == "cancelled"
