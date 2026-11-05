import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.staff import Staff
from app.models.coupon import Coupon
from app.services.auth_service import hash_password

TEST_DATABASE_URL = "sqlite:///./test_coupon_engine.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed initial test staff and coupons
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Staff
    staff = Staff(
        email="staff@couponengine.com",
        password_hash=hash_password("Password123!"),
        created_at=now,
    )
    db.add(staff)

    # Coupons
    c_active = Coupon(
        code="TESTACTIVE",
        discount_percent=20.0,
        expiry_date=now + timedelta(days=10),
        usage_limit=10,
        used_count=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    c_expired = Coupon(
        code="TESTEXPIRED",
        discount_percent=15.0,
        expiry_date=now - timedelta(days=2),
        usage_limit=10,
        used_count=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    c_disabled = Coupon(
        code="TESTDISABLED",
        discount_percent=10.0,
        expiry_date=now + timedelta(days=10),
        usage_limit=10,
        used_count=0,
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    c_maxed = Coupon(
        code="TESTMAXED",
        discount_percent=50.0,
        expiry_date=now + timedelta(days=10),
        usage_limit=3,
        used_count=3,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    db.add_all([c_active, c_expired, c_disabled, c_maxed])
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/auth/login",
        json={"email": "staff@couponengine.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
