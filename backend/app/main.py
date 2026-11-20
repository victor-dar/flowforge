from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai import AIProviderError, generate_answer, hybrid_context
from app.auth import create_token, get_current_user, get_db, hash_password, verify_password
from app.config import settings
from app.documents import DocumentProcessingError, extract_document_text
from app.models import Base, Chatbot, Conversation, KnowledgeDocument, Message, SessionLocal, User, engine
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
    return BotOut(id=bot.id, name=bot.name, business_name=bot.business_name, description=bot.description, instructions=bot.instructions, welcome_message=bot.welcome_message, color=bot.color, created_at=bot.created_at.isoformat() if bot.created_at else "", document_count=len(bot.documents))


def owned_bot(bot_id: int, owner_id: int, db: Session) -> Chatbot:
    bot = db.scalar(select(Chatbot).options(selectinload(Chatbot.documents)).where(Chatbot.id == bot_id, Chatbot.owner_id == owner_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
    return bot


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
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@app.post(
    "/api/auth/login",
    response_model=TokenOut,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/api/bots", response_model=list[BotOut])
def list_bots(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bots = db.scalars(select(Chatbot).options(selectinload(Chatbot.documents)).where(Chatbot.owner_id == user.id).order_by(Chatbot.id.desc())).all()
    return [bot_output(bot) for bot in bots]


@app.post("/api/bots", response_model=BotOut, status_code=201)
def create_bot(data: BotCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = Chatbot(owner_id=user.id, **data.model_dump())
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
    for key, value in data.model_dump(exclude_unset=True).items():
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
def get_public_bot(bot_id: int, db: Session = Depends(get_db)):
    bot = db.get(Chatbot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
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
    bot = db.scalar(select(Chatbot).options(selectinload(Chatbot.documents)).where(Chatbot.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
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
    db.add(Message(conversation_id=conversation.id, role="user", content=data.message))
    context = await hybrid_context(data.message, [document.content for document in bot.documents])
    try:
        answer = await generate_answer(bot.instructions, data.message, context)
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
