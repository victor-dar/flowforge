from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_and_bot_isolation():
    suffix = "test-user-flowforge@example.com"
    registered = client.post("/api/auth/register", json={"email": suffix, "password": "senha-segura-123"})
    assert registered.status_code in (201, 409)
    token = registered.json().get("access_token") if registered.status_code == 201 else client.post("/api/auth/login", json={"email": suffix, "password": "senha-segura-123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/bots", headers=headers, json={"name": "Assistente de teste"})
    assert created.status_code == 201
    assert created.json()["name"] == "Assistente de teste"
    assert client.get("/api/bots").status_code == 401


def test_password_hash_is_not_plaintext():
    from app.auth import hash_password, verify_password

    stored = hash_password("senha-de-teste")
    assert "senha-de-teste" not in stored
    assert verify_password("senha-de-teste", stored)
    assert not verify_password("outra-senha", stored)
