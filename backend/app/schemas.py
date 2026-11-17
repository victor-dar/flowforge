from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    business_name: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(default="Seja útil, claro e cordial.", max_length=4000)
    welcome_message: str = Field(default="Olá! Como posso ajudar?", max_length=500)
    color: str = Field(default="#6d5dfc", pattern=r"^#[0-9a-fA-F]{6}$")


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    business_name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = Field(default=None, max_length=4000)
    welcome_message: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    visitor_id: str = Field(min_length=1, max_length=100)
    conversation_id: int | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class BotOut(BaseModel):
    id: int
    name: str
    business_name: str
    description: str
    instructions: str
    welcome_message: str
    color: str
    created_at: str
    document_count: int = 0


class ChatOut(BaseModel):
    conversation_id: int
    answer: str
