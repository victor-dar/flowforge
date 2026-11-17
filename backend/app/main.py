from contextlib import asynccontextmanager
from io import BytesIO
import re

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import create_token, get_current_user, get_db, hash_password, verify_password
from app.config import settings
from app.models import Base, Chatbot, Conversation, KnowledgeDocument, Message, SessionLocal, User, engine
from app.schemas import BotCreate, BotOut, BotUpdate, ChatOut, ChatRequest, Credentials, TokenOut, UserOut
from app.ai import generate_answer, relevant_context


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FlowForge API", version="0.1.0", description="API para criar e publicar assistentes FlowForge", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


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


@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(data: Credentials, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado")
    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=TokenOut)
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
    if len(data) > settings.max_document_bytes:
        raise HTTPException(status_code=413, detail="O arquivo excede o limite de 5 MB")
    filename = file.filename or "documento.txt"
    if filename.lower().endswith(".pdf") or file.content_type == "application/pdf":
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Não foi possível ler o PDF") from exc
    elif filename.lower().endswith((".txt", ".md", ".csv")):
        text = data.decode("utf-8-sig", errors="replace")
    else:
        raise HTTPException(status_code=415, detail="Formato não suportado. Envie PDF, TXT, MD ou CSV.")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise HTTPException(status_code=422, detail="O arquivo não contém texto extraível")
    doc = KnowledgeDocument(bot_id=bot.id, name=filename[:255], content=text[:500_000])
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


@app.post("/api/public/bots/{bot_id}/chat", response_model=ChatOut)
async def public_chat(bot_id: int, data: ChatRequest, db: Session = Depends(get_db)):
    bot = db.scalar(select(Chatbot).options(selectinload(Chatbot.documents)).where(Chatbot.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot não encontrado")
    if data.conversation_id:
        conversation = db.scalar(select(Conversation).where(Conversation.id == data.conversation_id, Conversation.bot_id == bot_id, Conversation.visitor_id == data.visitor_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
    else:
        conversation = Conversation(bot_id=bot_id, visitor_id=data.visitor_id)
        db.add(conversation)
        db.flush()
    db.add(Message(conversation_id=conversation.id, role="user", content=data.message))
    context = relevant_context(data.message, [document.content for document in bot.documents])
    answer = await generate_answer(bot.instructions, data.message, context)
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()
    return ChatOut(conversation_id=conversation.id, answer=answer)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
