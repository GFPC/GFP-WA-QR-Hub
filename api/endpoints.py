from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import base64

from api.dependencies import get_db, verify_secret_key
from api.schemas import (
    WhatsAppQRUpdate, BotCreate, BotResponse, HealthCheck,
    WhatsAppBotRegisterRequest, WhatsAppBotCheckRegisterRequest,
    WhatsAppBotUpdateQRRequest, WhatsAppBotAuthedStateRequest,
    WhatsAppBotResponse
)
from db.repository import BotRepository
from bot.services.qr_manager import QRManager
from core.logger import logger

router = APIRouter()


@router.get("/status", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck()


@router.post("/qr_update", dependencies=[Depends(verify_secret_key)])
async def handle_qr_update(
        data: WhatsAppQRUpdate,
        db: AsyncSession = Depends(get_db)
):
    """Updates QR code for specified bot and notifies subscribed users"""
    repo = BotRepository(db)
    bot = await repo.get_bot(data.bot_id)

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    await repo.update_qr(data.bot_id, data.qr_data)
    await QRManager.notify_subscribed_users(data.bot_id, db)

    logger.info(f"QR updated for bot {data.bot_id}")
    return {"status": "success"}


@router.post("/bots", response_model=BotResponse)
async def create_bot(
        bot_data: BotCreate,
        db: AsyncSession = Depends(get_db)
):
    """Creates a new bot"""
    repo = BotRepository(db)
    bot = await repo.create_bot(
        bot_id=bot_data.name.lower().replace(" ", "_"),
        name=bot_data.name,
        description=bot_data.description
    )
    return BotResponse(
        id=bot.id,
        name=bot.name,
        description=bot.description,
        authed=bot.authed,
        created_at=bot.created_at.isoformat()
    )


# New WhatsApp bot integration endpoints
@router.post("/whatsapp/register", response_model=WhatsAppBotResponse)
async def whatsapp_bot_register(
    data: WhatsAppBotRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new WhatsApp bot"""
    repo = BotRepository(db)
    
    # Use the provided bot_id
    bot_id = data.bot.id
    
    # Check if bot already exists
    existing_bot = await repo.get_bot(bot_id)
    if existing_bot:
        return WhatsAppBotResponse(
            success=False,
            message="Bot already registered",
            data={"bot_id": bot_id}
        )
    
    # Create new bot
    bot = await repo.create_bot(
        bot_id=bot_id,
        name=data.bot.name,
        description=data.bot.description
    )
    
    logger.info(f"Registered new WhatsApp bot: {bot.id}")
    return WhatsAppBotResponse(
        success=True,
        message="Bot registered successfully",
        data={"bot_id": bot.id, "name": bot.name}
    )


@router.post("/whatsapp/check_register", response_model=WhatsAppBotResponse)
async def whatsapp_bot_check_register(
    data: WhatsAppBotCheckRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Check if WhatsApp bot is registered"""
    repo = BotRepository(db)
    bot = await repo.get_bot(data.bot_id)
    
    if not bot:
        return WhatsAppBotResponse(
            success=False,
            message="Bot not registered",
            data={"bot_id": data.bot_id}
        )
    
    return WhatsAppBotResponse(
        success=True,
        message="Bot is registered",
        data={
            "bot_id": bot.id,
            "name": bot.name,
            "description": bot.description,
            "authed": bot.authed
        }
    )


@router.post("/whatsapp/update_qr", response_model=WhatsAppBotResponse)
async def whatsapp_bot_update_qr(
    data: WhatsAppBotUpdateQRRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update QR code for WhatsApp bot"""
    repo = BotRepository(db)
    bot = await repo.get_bot(data.bot_id)
    
    if not bot:
        return WhatsAppBotResponse(
            success=False,
            message="Bot not found",
            data={"bot_id": data.bot_id}
        )
    
    try:
        # Проверяем формат QR данных
        qr_data = data.qr_data
        
        # Если QR приходит в формате WhatsApp (строка с запятыми)
        if ',' in qr_data:
            # Берем первую часть QR кода (до первой запятой)
            qr_data = qr_data.split(',')[0]
        
        # Проверяем, что это валидный base64
        try:
            base64.b64decode(qr_data)
        except Exception:
            return WhatsAppBotResponse(
                success=False,
                message="Invalid QR code format",
                data={"bot_id": data.bot_id}
            )
        
        # Сохраняем QR код
        await repo.update_qr(data.bot_id, qr_data)
        await QRManager.notify_subscribed_users(data.bot_id, db)
        
        logger.info(f"QR updated for WhatsApp bot: {data.bot_id}")
        return WhatsAppBotResponse(
            success=True,
            message="QR code updated successfully",
            data={"bot_id": data.bot_id}
        )
    except Exception as e:
        logger.error(f"Error updating QR code: {e}")
        return WhatsAppBotResponse(
            success=False,
            message=f"Error updating QR code: {str(e)}",
            data={"bot_id": data.bot_id}
        )


@router.post("/whatsapp/update_auth_state", response_model=WhatsAppBotResponse)
async def whatsapp_bot_update_auth_state(
    data: WhatsAppBotAuthedStateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update authentication state for WhatsApp bot"""
    repo = BotRepository(db)
    bot = await repo.get_bot(data.bot_id)
    
    if not bot:
        return WhatsAppBotResponse(
            success=False,
            message="Bot not found",
            data={"bot_id": data.bot_id}
        )
    
    # Update authentication state
    authed = data.state == "authed"
    await repo.update_auth_state(data.bot_id, authed)
    
    logger.info(f"Auth state updated for WhatsApp bot {data.bot_id}: {data.state}")
    return WhatsAppBotResponse(
        success=True,
        message=f"Authentication state updated to {data.state}",
        data={"bot_id": data.bot_id, "authed": authed}
    )
