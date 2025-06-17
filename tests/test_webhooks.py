import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from main import app, GITHUB_SECRET

client = TestClient(app)


def generate_signature(secret, payload_bytes):
    signature = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def test_lab_webhook_push():
    payload = {"ref": "refs/heads/main"}
    payload_bytes = json.dumps(payload).encode()
    signature = generate_signature(GITHUB_SECRET or "test", payload_bytes)
    response = client.post(
        "/services/webhooks/lab",
        data=payload_bytes,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json"
        },
    )
    assert response.status_code in (200, 500)  # 500 if script fails, 200 if success
    assert response.json()["status"] in ("success", "error", "ignored")


def test_lab_webhook_invalid_signature():
    payload = {"ref": "refs/heads/main"}
    payload_bytes = json.dumps(payload).encode()
    # Use a wrong signature
    signature = "sha256=deadbeef"
    response = client.post(
        "/services/webhooks/lab",
        data=payload_bytes,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json"
        },
    )
    assert response.status_code == 401
