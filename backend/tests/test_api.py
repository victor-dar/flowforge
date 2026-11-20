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


def test_metrics_require_authentication(client):
    assert client.get("/metrics").status_code == 401
    assert client.get("/api/metrics").status_code == 401

    headers = auth_headers(client)
    public_metrics = client.get("/metrics", headers=headers)
    api_metrics = client.get("/api/metrics", headers=headers)

    assert public_metrics.status_code == 200
    assert api_metrics.status_code == 200
    public_data = public_metrics.json()
    api_data = api_metrics.json()
    assert {
        key: public_data[key]
        for key in ("users", "bots", "documents", "conversations", "messages")
    } == {
        key: api_data[key]
        for key in ("users", "bots", "documents", "conversations", "messages")
    }


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


def test_retention_cleanup_accepts_configured_policy(client, monkeypatch):
    monkeypatch.setattr(settings, "retention_days", 30)
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Retencao"},
    ).json()
    chat = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "Oi", "visitor_id": "old-visitor"},
    )
    assert chat.status_code == 200

    cleaned = client.post("/api/account/retention/cleanup", headers=headers)
    assert cleaned.status_code == 200
    assert cleaned.json()["deleted_conversations"] == 0
    assert cleaned.json()["retention_days"] == 30


def test_account_export_and_delete(client):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Dados exportáveis"},
    ).json()
    client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=headers,
        files={"file": ("base.txt", b"Conteudo exportavel.", "text/plain")},
    )

    exported = client.get("/api/account/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["user"]["email"] == "owner@example.com"
    assert exported.json()["bots"][0]["name"] == "Dados exportáveis"
    assert exported.json()["bots"][0]["documents"][0]["content"] == "Conteudo exportavel."

    deleted = client.delete("/api/account", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/bots", headers=headers).status_code == 401


def test_login_rejects_invalid_password_and_me_returns_authenticated_user(client):
    headers = auth_headers(client)
    invalid_login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "senha-errada"},
    )
    assert invalid_login.status_code == 401

    profile = client.get("/api/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "owner@example.com"


def test_email_verification_and_password_reset_tokens(client):
    from app.auth import create_action_token

    credentials = {"email": "actions@example.com", "password": "senha-segura-123"}
    registered = client.post("/api/auth/register", json=credentials)
    assert registered.status_code == 201
    user_id = registered.json()["user"]["id"]

    verify_token = create_action_token(user_id, "email-verification", 1440)
    verified = client.post(
        "/api/auth/verify/confirm",
        json={"token": verify_token},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "E-mail verificado"

    reset_token = create_action_token(user_id, "password-reset", 30)
    reset = client.post(
        "/api/auth/password/reset/confirm",
        json={"token": reset_token, "password": "nova-senha-segura-123"},
    )
    assert reset.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    new_login = client.post(
        "/api/auth/login",
        json={"email": credentials["email"], "password": "nova-senha-segura-123"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


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
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == document["id"]
    assert listed.json()[0]["name"] == "guia.txt"
    assert listed.json()[0]["size_chars"] == len("Conteudo do documento.")
    assert listed.json()[0]["created_at"]

    deleted = client.delete(
        f"/api/bots/{bot['id']}/documents/{document['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/bots/{bot['id']}/documents", headers=headers).json() == []


def test_documents_are_private_to_the_bot_owner(client):
    owner_headers = auth_headers(client, "document-owner@example.com")
    other_headers = auth_headers(client, "document-other@example.com")
    bot = client.post(
        "/api/bots",
        headers=owner_headers,
        json={"name": "Base privada"},
    ).json()
    document = client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=owner_headers,
        files={"file": ("privado.txt", b"Informacao privada.", "text/plain")},
    ).json()

    assert client.get(
        f"/api/bots/{bot['id']}/documents",
        headers=other_headers,
    ).status_code == 404
    assert client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=other_headers,
        files={"file": ("outro.txt", b"Outro conteudo.", "text/plain")},
    ).status_code == 404
    assert client.delete(
        f"/api/bots/{bot['id']}/documents/{document['id']}",
        headers=other_headers,
    ).status_code == 404
    listed = client.get(
        f"/api/bots/{bot['id']}/documents",
        headers=owner_headers,
    ).json()
    assert len(listed) == 1
    assert listed[0]["id"] == document["id"]
    assert listed[0]["name"] == "privado.txt"
    assert listed[0]["size_chars"] == len("Informacao privada.")


def test_uploaded_document_is_used_in_chat_and_deleted_content_is_not_retrieved(
    client, monkeypatch
):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Assistente com documentos"},
    ).json()
    uploaded = client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=headers,
        files={
            "file": (
                "horarios.txt",
                "A cafeteria abre às 9 horas. Fecha às 18 horas.".encode(),
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201
    observed_contexts = []

    async def capture_context(instructions, question, context, history=None):
        observed_contexts.append(context)
        return "Resposta de teste"

    monkeypatch.setattr("app.main.generate_answer", capture_context)
    payload = {"message": "Qual o horario da cafeteria?", "visitor_id": "visitor-doc"}
    chat = client.post(f"/api/public/bots/{bot['id']}/chat", json=payload)

    assert chat.status_code == 200
    assert observed_contexts == ["A cafeteria abre às 9 horas."]
    conversation = client.get(
        f"/api/bots/{bot['id']}/conversations",
        headers=headers,
    ).json()
    assert {
        message["role"]: message["content"]
        for message in conversation[0]["messages"]
    } == {
        "user": payload["message"],
        "assistant": "Resposta de teste",
    }

    deleted = client.delete(
        f"/api/bots/{bot['id']}/documents/{uploaded.json()['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    continued = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={
            **payload,
            "message": "Qual o horario da cafeteria?",
            "conversation_id": chat.json()["conversation_id"],
        },
    )

    assert continued.status_code == 200
    assert observed_contexts == ["A cafeteria abre às 9 horas.", ""]


def test_document_upload_rejects_unsupported_and_oversized_files(client, monkeypatch):
    headers = auth_headers(client)
    bot = client.post("/api/bots", headers=headers, json={"name": "Uploads"}).json()

    unsupported = client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=headers,
        files={"file": ("arquivo.exe", b"conteudo", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    monkeypatch.setattr(settings, "max_document_bytes", 4)
    oversized = client.post(
        f"/api/bots/{bot['id']}/documents",
        headers=headers,
        files={"file": ("grande.txt", b"cinco!", "text/plain")},
    )
    assert oversized.status_code == 413
    assert client.get(f"/api/bots/{bot['id']}/documents", headers=headers).json() == []


def test_greeting_without_ai_provider_has_a_direct_response(client):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Cafeteria"},
    ).json()

    response = client.post(
        f"/api/public/bots/{bot['id']}/chat",
        json={"message": "oi", "visitor_id": "greeting-test"},
    )

    assert response.status_code == 200
    assert "Como posso ajudar" in response.json()["answer"]


def test_allowed_widget_domains_reject_unlisted_origin(client):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={
            "name": "Site restrito",
            "allowed_domains": ["https://site-autorizado.com"],
        },
    ).json()

    denied = client.post(
        "/api/widget/capability",
        params={
            "bot_id": bot["id"],
            "origin": "https://site-nao-autorizado.com",
        },
        headers={"Referer": "https://site-nao-autorizado.com/page"},
    )
    allowed = client.post(
        "/api/widget/capability",
        params={
            "bot_id": bot["id"],
            "origin": "https://site-autorizado.com",
        },
        headers={"Referer": "https://site-autorizado.com/page"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    capability = allowed.json()["capability"]
    public = client.get(
        f"/api/public/bots/{bot['id']}",
        params={"capability": capability},
    )
    assert public.status_code == 200


def test_widget_capability_rejects_direct_tampered_and_mismatched_requests(client):
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={
            "name": "Widget protegido",
            "allowed_domains": ["https://loja-autorizada.com"],
        },
    ).json()

    client.cookies.clear()
    direct = client.get(f"/api/public/bots/{bot['id']}")
    assert direct.status_code == 403

    mismatched_referer = client.post(
        "/api/widget/capability",
        params={"bot_id": bot["id"], "origin": "https://loja-autorizada.com"},
        headers={"Referer": "https://outro-dominio.com/page"},
    )
    assert mismatched_referer.status_code == 403

    allowed = client.post(
        "/api/widget/capability",
        params={"bot_id": bot["id"], "origin": "https://loja-autorizada.com"},
        headers={"Referer": "https://loja-autorizada.com/page"},
    )
    assert allowed.status_code == 200
    capability = allowed.json()["capability"]

    tampered = capability[:-1] + ("A" if capability[-1] != "A" else "B")
    rejected = client.get(
        f"/api/public/bots/{bot['id']}",
        params={"capability": tampered},
    )
    assert rejected.status_code == 403


def test_widget_capability_endpoint_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "widget_capability_per_minute", 1)
    headers = auth_headers(client)
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Widget limitado"},
    ).json()

    first = client.post(
        "/api/widget/capability",
        params={"bot_id": bot["id"], "origin": "http://localhost"},
    )
    second = client.post(
        "/api/widget/capability",
        params={"bot_id": bot["id"], "origin": "http://localhost"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


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

    async def fake_answer(instructions, question, context, history=None):
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

    async def fail_answer(instructions, question, context, history=None):
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
