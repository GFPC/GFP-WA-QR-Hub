from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class WhatsAppQRUpdate(BaseModel):
    bot_id: str = Field(..., min_length=32, max_length=32)
    qr_data: str
    secret: str = Field(..., min_length=32)


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., max_length=200)


class BotResponse(BaseModel):
    id: str
    name: str
    description: str
    authed: bool
    created_at: str


class UserResponse(BaseModel):
    tg_id: int
    data: Dict[str, Any]
    created_at: str


class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


# New schemas for WhatsApp bot integration
class WhatsAppBotData(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., max_length=200)


class WhatsAppBotRegisterRequest(BaseModel):
    bot: WhatsAppBotData


class WhatsAppBotCheckRegisterRequest(BaseModel):
    bot_id: str = Field(..., min_length=32, max_length=32)


class WhatsAppBotUpdateQRRequest(BaseModel):
    bot_id: str = Field(..., min_length=32, max_length=32)
    qr_data: str


class WhatsAppBotAuthedStateRequest(BaseModel):
    bot_id: str = Field(..., min_length=32, max_length=32)
    state: str = Field(..., pattern="^(authed|not_authed)$")


class WhatsAppBotResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class CustomNotificationRequest(BaseModel):
    """Schema for custom notification requests from WhatsApp bot"""
    message: str = Field(..., description="The message to send")
    sender_name: str = Field("WhatsApp Bot", description="Name of the sender (e.g., 'WhatsApp Bot', 'John Doe')")
    bot_id: str = Field(..., description="The ID of the WhatsApp bot sending the notification")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello from your WhatsApp bot!",
                "sender_name": "My Awesome WhatsApp Bot",
                "bot_id": "my_whatsapp_bot_id"
            }
        } 