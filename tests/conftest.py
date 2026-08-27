from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = Path(__file__).resolve().parent / "test_ecommerce.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MERCHANT_REVIEW_HOURS"] = "48"
os.environ["RETURN_DEADLINE_DAYS"] = "7"
os.environ["RECEIPT_CONFIRM_HOURS"] = "72"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Product, User
from app.security import hash_password


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def actors(db):
    password = hash_password("123456")
    user = User(username="user", display_name="测试用户", password_hash=password, role="user")
    merchant1 = User(username="merchant1", display_name="商家一", password_hash=password, role="merchant")
    merchant2 = User(username="merchant2", display_name="商家二", password_hash=password, role="merchant")
    service = User(username="service", display_name="客服", password_hash=password, role="customer_service")
    tech = User(username="tech", display_name="技术管理员", password_hash=password, role="tech_admin")
    db.add_all([user, merchant1, merchant2, service, tech])
    db.flush()
    p1 = Product(merchant_id=merchant1.id, name="商品A", category="测试", description="A", price_cents=10000, stock=20, image_url="")
    p2 = Product(merchant_id=merchant2.id, name="商品B", category="测试", description="B", price_cents=20000, stock=20, image_url="")
    db.add_all([p1, p2])
    db.commit()
    return {"user": user, "merchant1": merchant1, "merchant2": merchant2, "service": service, "tech": tech, "p1": p1, "p2": p2}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
