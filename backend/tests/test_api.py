import base64
import hashlib

import pytest

from app.config import Settings, settings


def register(client, email="owner@example.com", password="senha-segura-123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(client, email="owner@example.com"):
    result = register(client, email=email)
    return {"Authorization": f"Bearer {result['access_token']}"}


def test_healthcheck(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_duplicate_email(client):
    credentials = {"email": "owner@example.com", "password": "senha-segura-123"}
    registered = client.post("/api/auth/register", json=credentials)
    assert registered.status_code == 201
    assert registered.json()["token_type"] == "bearer"

    logged_in = client.post("/api/auth/login", json=credentials)
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["email"] == credentials["email"]

    duplicate = client.post("/api/auth/register", json=credentials)
    assert duplicate.status_code == 409


def test_authentication_requests_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 1)
    credentials = {"email": "missing@example.com", "password": "senha-segura-123"}

    first = client.post("/api/auth/login", json=credentials)
    second = client.post("/api/auth/login", json=credentials)

    assert first.status_code == 401
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0


def test_chatbots_are_isolated_between_users(client):
    first_headers = auth_headers(client, "first@example.com")
    second_headers = auth_headers(client, "second@example.com")
    created = client.post(
        "/api/bots",
        headers=first_headers,
        json={"name": "Assistente privado"},
    )
    bot_id = created.json()["id"]

    assert client.get(f"/api/bots/{bot_id}", headers=second_headers).status_code == 404
    assert client.get("/api/bots", headers=second_headers).json() == []
    assert client.get("/api/bots").status_code == 401


def test_rejects_tampered_bearer_token(client):
    token = register(client)["access_token"]
    header, payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    tampered = f"{header}.{payload}.{replacement}{signature[1:]}"

    response = client.get(
        "/api/bots",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_password_hash_is_not_plaintext_and_reads_legacy_hashes():
    from app.auth import hash_password, verify_password

    password = "senha-de-teste"
    stored = hash_password(password)
    assert password not in stored
    assert verify_password(password, stored)
    assert not verify_password("senha-incorreta", stored)

    salt = b"legacy-salt-1234"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    legacy_hash = (
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )
    assert verify_password(password, legacy_hash)


def test_upload_list_and_delete_document(client):
    headers = auth_headers(client)
    bot = client.post("/api/bots", headers=headers, json={"name": "Base"}).json()
    uploaded = client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=headers,
        files={"file": ("guia.txt", b"Conteudo do documento.", "text/plain")},
    )
    assert uploaded.status_code == 201
    document = uploaded.json()

    listed = client.get(f"/api/bots/{bot['id']}/documents", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [{"id": document["id"], "name": "guia.txt"}]

    deleted = client.delete(
        f"/api/bots/{bot['id']}/documents/{document['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/bots/{bot['id']}/documents", headers=headers).json() == []


def test_public_widget_and_chat(client, monkeypatch):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Assistente público", "welcome_message": "Boas-vindas"},
    ).json()

    public_bot = client.get(f"/api/public/bots/{bot['id']}")
    assert public_bot.status_code == 200
    assert public_bot.json()["welcome_message"] == "Boas-vindas"
    assert "instructions" not in public_bot.json()
    assert 'id="form"' in client.get("/widget").text
    assert "data-bot-id" in client.get("/widget.js").text

    async def fake_answer(instructions, question, context):
        return "Resposta de teste"

    monkeypatch.setattr("app.main.generate_answer", fake_answer)
    chat = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "Olá", "visitor_id": "visitor-1"},
    )
    assert chat.status_code == 200
    assert chat.json()["answer"] == "Resposta de teste"


def test_daily_chat_limit_is_shared_by_bot(client, monkeypatch):
    headers = auth_headers(client)
    bot = client.post("/api/bots", headers=headers, json={"name": "Limitado"}).json()
    monkeypatch.setattr(settings, "public_chat_daily_limit_per_bot", 1)
    payload = {"message": "Olá", "visitor_id": "visitor-1"}

    first = client.post(f"/api/public/bots/{bot['id']}/chat", json=payload)
    second = client.post(f"/api/public/bots/{bot['id']}/chat", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0


def test_invalid_conversation_does_not_consume_daily_bot_quota(client, monkeypatch):
    headers = auth_headers(client)
    bot = client.post("/api/bots", headers=headers, json={"name": "Limitado"}).json()
    monkeypatch.setattr(settings, "public_chat_daily_limit_per_bot", 1)

    invalid = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "Olá", "visitor_id": "visitor-1", "conversation_id": 999},
    )
    valid = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "Olá", "visitor_id": "visitor-1"},
    )

    assert invalid.status_code == 404
    assert valid.status_code == 200


def test_provider_failure_returns_503_without_saving_chat(client, monkeypatch):
    from app.ai import AIProviderError

    headers = auth_headers(client)
    bot = client.post("/api/bots", headers=headers, json={"name": "Sem provedor"}).json()

    async def fail_answer(instructions, question, context):
        raise AIProviderError("O serviço de IA está indisponível no momento. Tente novamente.")

    monkeypatch.setattr("app.main.generate_answer", fail_answer)
    response = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "Olá", "visitor_id": "visitor-1"},
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    assert client.get(f"/api/bots/{bot['id']}/conversations", headers=headers).json() == []


def test_ai_client_wraps_network_errors(monkeypatch):
    import asyncio

    import httpx

    from app.ai import AIProviderError, generate_answer

    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fail_request(self, *args, **kwargs):
        raise httpx.ConnectError(
            "simulated network failure",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fail_request)

    with pytest.raises(AIProviderError, match="indisponível"):
        asyncio.run(generate_answer("instruções", "pergunta", ""))


def test_production_rejects_default_secret_and_wildcard_cors():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(app_env="production").validate_deployment()

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            secret_key="a-strong-unique-secret-key-at-least-32",
            cors_origins="https://app.example.com,*",
        ).validate_deployment()


def test_application_startup_rejects_default_production_secret(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "secret_key", "change-this-secret-before-deploying")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        with TestClient(app):
            pass
