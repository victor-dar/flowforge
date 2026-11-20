from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai import (
    AIProviderError,
    chunk_text,
    embed_text,
    generate_answer,
    hybrid_chunk_context,
)
from app.auth import create_token, get_current_user, get_db, hash_password, verify_password
from app.config import settings
from app.documents import DocumentProcessingError, extract_document_text
from app.models import (
    Base,
    Chatbot,
    Conversation,
    DocumentChunk,
    KnowledgeDocument,
    Message,
    SessionLocal,
    User,
    engine,
)
from app.schemas import BotCreate, BotOut, BotUpdate, ChatOut, ChatRequest, Credentials, TokenOut, UserOut
from app.rate_limit import client_address, consume_rate_limit
from app.widget_page import WIDGET_HTML


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_deployment()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FlowForge API", version="0.2.0", description="API para criar e publicar assistentes FlowForge", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = perf_counter()
        response = await call_next(request)
        logging.getLogger("flowforge.request").info(
            json.dumps(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
                ensure_ascii=False,
            )
        )
        return response


app.add_middleware(RequestLoggingMiddleware)


def bot_output(bot: Chatbot) -> BotOut:
    return BotOut(
        id=bot.id,
        name=bot.name,
        business_name=bot.business_name,
        description=bot.description,
        instructions=bot.instructions,
        welcome_message=bot.welcome_message,
        color=bot.color,
        allowed_domains=[
            item.strip()
            for item in (bot.allowed_domains or "").split(",")
            if item.strip()
        ],
        created_at=bot.created_at.isoformat() if bot.created_at else "",
        document_count=len(bot.documents),
    )


def normalize_domains(domains: list[str]) -> str:
    normalized: list[str] = []
    for domain in domains:
        value = domain.strip().lower().rstrip("/")
        if value.startswith(("http://", "https://")):
            normalized.append(value)
        elif value:
            normalized.append(f"https://{value}")
    return ",".join(dict.fromkeys(normalized))


def owned_bot(bot_id: int, owner_id: int, db: Session) -> Chatbot:
    bot = db.scalar(
        select(Chatbot)
        .options(
            selectinload(Chatbot.documents).selectinload(KnowledgeDocument.chunks)
        )
        .where(Chatbot.id == bot_id, Chatbot.owner_id == owner_id)
    )
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
    return bot


def validate_public_origin(request: Request, bot: Chatbot) -> None:
    allowed = [
        item.strip().lower().rstrip("/")
        for item in (bot.allowed_domains or "").split(",")
        if item.strip()
    ]
    if not allowed:
        return
    candidate_headers = [
        request.headers.get("origin"),
        request.headers.get("x-flowforge-origin"),
        request.headers.get("referer"),
    ]
    origins: set[str] = set()
    for candidate in candidate_headers:
        if candidate:
            parsed = urlparse(candidate.strip())
            if parsed.scheme and parsed.hostname:
                origins.add(f"{parsed.scheme.lower()}://{parsed.netloc.lower().rstrip('/')}")
    if not any(origin in allowed for origin in origins):
        raise HTTPException(status_code=403, detail="Origem não autorizada para este assistente")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    bot_count = db.scalar(select(func.count()).select_from(Chatbot)) or 0
    document_count = db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0
    conversation_count = db.scalar(select(func.count()).select_from(Conversation)) or 0
    message_count = db.scalar(select(func.count()).select_from(Message)) or 0
    return {
        "users": user_count,
        "bots": bot_count,
        "documents": document_count,
        "conversations": conversation_count,
        "messages": message_count,
    }


def enforce_auth_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    address = client_address(request.client.host if request.client else None)
    consume_rate_limit(
        db,
        f"auth:{address}",
        settings.auth_rate_limit_per_minute,
        60,
    )


@app.get("/widget.js")
def widget_script():
    return Response(
        content=(Path(__file__).parent / "widget.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


@app.get("/widget", response_class=HTMLResponse)
def widget_page():
    return WIDGET_HTML


@app.post(
    "/api/auth/register",
    response_model=TokenOut,
    status_code=201,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def register(data: Credentials, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado")
    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    payload = TokenOut(access_token=token, user=UserOut.model_validate(user))
    response = JSONResponse(payload.model_dump(), status_code=201)
    response.set_cookie(
        "flowforge_access",
        token,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
    )
    return response


@app.post(
    "/api/auth/login",
    response_model=TokenOut,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    token = create_token(user.id)
    payload = TokenOut(access_token=token, user=UserOut.model_validate(user))
    response = JSONResponse(payload.model_dump())
    response.set_cookie(
        "flowforge_access",
        token,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
    )
    return response


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        "flowforge_access",
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="lax",
    )
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/api/bots", response_model=list[BotOut])
def list_bots(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bots = db.scalars(select(Chatbot).options(selectinload(Chatbot.documents)).where(Chatbot.owner_id == user.id).order_by(Chatbot.id.desc())).all()
    return [bot_output(bot) for bot in bots]


@app.post("/api/bots", response_model=BotOut, status_code=201)
def create_bot(data: BotCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = data.model_dump()
    allowed_domains = normalize_domains(values.pop("allowed_domains", []))
    bot = Chatbot(owner_id=user.id, allowed_domains=allowed_domains, **values)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot_output(bot)


@app.get("/api/bots/{bot_id}", response_model=BotOut)
def get_bot(bot_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return bot_output(owned_bot(bot_id, user.id, db))


@app.get("/api/bots/{bot_id}/documents")
def list_documents(bot_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_bot(bot_id, user.id, db)
    documents = db.scalars(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.bot_id == bot_id)
        .order_by(KnowledgeDocument.id)
    ).all()
    return [{"id": document.id, "name": document.name} for document in documents]


@app.patch("/api/bots/{bot_id}", response_model=BotOut)
def update_bot(bot_id: int, data: BotUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = owned_bot(bot_id, user.id, db)
    changes = data.model_dump(exclude_unset=True)
    if "allowed_domains" in changes:
        changes["allowed_domains"] = normalize_domains(changes["allowed_domains"] or [])
    for key, value in changes.items():
        setattr(bot, key, value)
    db.commit()
    db.refresh(bot)
    return bot_output(bot)


@app.delete("/api/bots/{bot_id}", status_code=204)
def delete_bot(bot_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = owned_bot(bot_id, user.id, db)
    db.delete(bot)
    db.commit()


@app.post("/api/bots/{bot_id}/documents", status_code=201)
async def upload_document(bot_id: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = owned_bot(bot_id, user.id, db)
    data = await file.read(settings.max_document_bytes + 1)
    filename = file.filename or "documento.txt"
    try:
        text = extract_document_text(
            filename=filename,
            content_type=file.content_type,
            data=data,
            max_upload_bytes=settings.max_document_bytes,
            max_text_characters=settings.max_document_characters,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    doc = KnowledgeDocument(bot_id=bot.id, name=filename[:255], content=text)
    db.add(doc)
    db.flush()
    for position, chunk in enumerate(chunk_text(text)):
        embedding: list[float] = []
        if settings.openai_api_key:
            try:
                embedding = await embed_text(chunk)
            except Exception:
                logging.getLogger("flowforge.documents").exception(
                    "Falha ao gerar embedding do documento; preservando chunk sem embedding"
                )
        db.add(
            DocumentChunk(
                document_id=doc.id,
                position=position,
                content=chunk,
                embedding=json.dumps(embedding) if embedding else "",
            )
        )
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "name": doc.name}


@app.delete("/api/bots/{bot_id}/documents/{document_id}", status_code=204)
def delete_document(bot_id: int, document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_bot(bot_id, user.id, db)
    doc = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.bot_id == bot_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    db.delete(doc)
    db.commit()


@app.get("/api/bots/{bot_id}/conversations")
def list_conversations(bot_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_bot(bot_id, user.id, db)
    conversations = db.scalars(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.bot_id == bot_id).order_by(Conversation.id.desc()).limit(100)).all()
    return [{"id": item.id, "visitor_id": item.visitor_id, "created_at": item.created_at.isoformat() if item.created_at else "", "messages": [{"role": message.role, "content": message.content, "created_at": message.created_at.isoformat() if message.created_at else ""} for message in item.messages]} for item in conversations]


@app.get("/api/public/bots/{bot_id}")
def get_public_bot(bot_id: int, request: Request, db: Session = Depends(get_db)):
    bot = db.get(Chatbot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
    validate_public_origin(request, bot)
    return {
        "id": bot.id,
        "name": bot.name,
        "welcome_message": bot.welcome_message,
        "color": bot.color,
    }


@app.post("/api/public/bots/{bot_id}/chat", response_model=ChatOut)
async def public_chat(
    bot_id: int,
    data: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    bot = db.scalar(
        select(Chatbot)
        .options(
            selectinload(Chatbot.documents).selectinload(KnowledgeDocument.chunks)
        )
        .where(Chatbot.id == bot_id)
    )
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
    validate_public_origin(request, bot)
    conversation = None
    if data.conversation_id:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.bot_id == bot_id,
                Conversation.visitor_id == data.visitor_id,
            )
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")

    address = client_address(request.client.host if request.client else None)
    consume_rate_limit(
        db,
        f"chat-ip:{address}",
        settings.public_chat_rate_limit_per_minute,
        60,
    )
    consume_rate_limit(
        db,
        f"chat-bot:{bot_id}",
        settings.public_chat_daily_limit_per_bot,
        86400,
    )

    if conversation is None:
        conversation = Conversation(bot_id=bot_id, visitor_id=data.visitor_id)
        db.add(conversation)
        db.flush()
    previous_messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(6)
    ).all()
    history = [
        {"role": message.role, "content": message.content[:1000]}
        for message in reversed(previous_messages)
        if message.role in {"user", "assistant"}
    ]
    db.add(Message(conversation_id=conversation.id, role="user", content=data.message))
    persisted_chunks: list[tuple[str, list[float] | None]] = []
    for document in bot.documents:
        for chunk in document.chunks:
            try:
                embedding = json.loads(chunk.embedding) if chunk.embedding else None
            except (json.JSONDecodeError, TypeError):
                embedding = None
            persisted_chunks.append((chunk.content, embedding))
    if persisted_chunks:
        context = await hybrid_chunk_context(data.message, persisted_chunks)
    else:
        context = await hybrid_chunk_context(
            data.message,
            [(chunk, None) for document in bot.documents for chunk in chunk_text(document.content)],
        )
    try:
        answer = await generate_answer(
            bot.instructions,
            data.message,
            context,
            history,
        )
    except AIProviderError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=str(exc),
            headers={"Retry-After": "30"},
        ) from exc
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()
    return ChatOut(conversation_id=conversation.id, answer=answer)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
