import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from models import Base
from database import get_db

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_email_registration_and_login():
    # Register
    resp = client.post(
        "/services/auth/email/register",
        data={
            "email": "test@example.com",
            "password": "testpass",
            "full_name": "Test User"
        }
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # Login
    resp = client.post(
        "/services/auth/email/login",
        data={"email": "test@example.com", "password": "testpass"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    # Get current user
    resp = client.get(f"/services/auth/me?token={token}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_create_payment_session(monkeypatch):
    # Register and login
    resp = client.post(
        "/services/auth/email/register",
        data={
            "email": "pay@example.com",
            "password": "paypass",
            "full_name": "Pay User"
        }
    )
    token = resp.json()["access_token"]

    # Mock FlexPay session creation
    def mock_create_flexpay_session(**kwargs):
        return {
            "id": "mock-payment-id",
            "redirect_url": "https://flexpay.com/pay/mock-payment-id"
        }
    monkeypatch.setattr(
        "flexpay.create_flexpay_session",
        lambda *a, **k: mock_create_flexpay_session(**k)
    )

    # Create payment session
    resp = client.post(
        "/services/sponsors/create-payment-session",
        data={"plan_type": "individual", "token": token}
    )
    assert resp.status_code == 200
    assert resp.json()["redirect_url"].startswith("https://flexpay.com/pay/")


def test_flexpay_webhook_and_invoice(monkeypatch):
    # Register and login
    resp = client.post(
        "/services/auth/email/register",
        data={
            "email": "invoice@example.com",
            "password": "invpass",
            "full_name": "Invoice User"
        }
    )
    token = resp.json()["access_token"]

    # Mock FlexPay session creation
    def mock_create_flexpay_session(**kwargs):
        return {
            "id": "inv-payment-id",
            "redirect_url": "https://flexpay.com/pay/inv-payment-id"
        }
    monkeypatch.setattr(
        "flexpay.create_flexpay_session",
        lambda *a, **k: mock_create_flexpay_session(**k)
    )

    # Create payment session
    resp = client.post(
        "/services/sponsors/create-payment-session",
        data={"plan_type": "individual", "token": token}
    )
    assert resp.status_code == 200

    # Simulate webhook
    webhook_payload = {
        "id": "inv-payment-id",
        "status": "completed",
        "invoice_url": "https://flexpay.com/invoice/inv-payment-id.pdf"
    }
    resp = client.post(
        "/services/sponsors/flexpay-webhook",
        json=webhook_payload
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Check sponsorships and invoice
    resp = client.get(f"/services/sponsors/my-sponsorships?token={token}")
    assert resp.status_code == 200
    sponsorships = resp.json()
    assert any(
        s["invoice_url"] == webhook_payload["invoice_url"] for s in sponsorships
    )
    assert any(s["payment_status"] == "completed" for s in sponsorships)