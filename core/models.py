from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WhatsAppBot(BaseModel):
    id: str
    user_id: int
    is_active: bool = True
    last_qr_message_id: Optional[int] = None
    last_qr_update: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QRUpdate(BaseModel):
    qr_data: str
    bot_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QRRequest(BaseModel):
    qr_data: str
    bot_id: str
    secret: str 