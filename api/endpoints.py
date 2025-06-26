import tempfile

import qrcode
from aiogram.types import FSInputFile
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import base64

from api.dependencies import get_db, verify_secret_key
from api.schemas import (
    WhatsAppQRUpdate, BotCreate, BotResponse, HealthCheck,
    WhatsAppBotRegisterRequest, WhatsAppBotCheckRegisterRequest,
    WhatsAppBotUpdateQRRequest, WhatsAppBotAuthedStateRequest,
    WhatsAppBotResponse,
    CustomNotificationRequest
)
from db.repository import BotRepository, UserRepository
from bot.services.qr_manager import QRManager
from bot.services.bot_connector import bot_connector
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
    await QRManager.notify_subscribed_users(data.bot_id, db, bot_connector.bot)

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

        # Проверяем формат QR данных
    qr_data = data.qr_data

    # Сохраняем QR код
    await repo.update_qr(data.bot_id, qr_data)
    await QRManager.notify_subscribed_users(data.bot_id, db, bot_connector.bot)

    logger.info(f"QR updated for WhatsApp bot: {data.bot_id}")
    return WhatsAppBotResponse(
        success=True,
        message="QR code updated successfully",
        data={"bot_id": data.bot_id}
    )


@router.post("/whatsapp/update_auth_state", response_model=WhatsAppBotResponse)
async def whatsapp_bot_update_auth_state(
        data: WhatsAppBotAuthedStateRequest,
        db: AsyncSession = Depends(get_db)
):
    """Update authentication state for WhatsApp bot"""
    repo = BotRepository(db)
    user_repo = UserRepository(db)
    bot = await repo.get_bot(data.bot_id)

    if not bot:
        return WhatsAppBotResponse(
            success=False,
            message="Bot not found",
            data={"bot_id": data.bot_id}
        )
    previous_authed = bot.authed

    # Update authentication state
    authed = data.state == "authed"
    await repo.update_auth_state(data.bot_id, authed)

    if authed and (previous_authed != authed):
        await QRManager.notify_auth_success(data.bot_id, db, bot_connector.bot)
    elif not authed and (previous_authed != authed):
        await QRManager.notify_deauth_success(data.bot_id, db, bot_connector.bot)

        users = await user_repo.get_users_linked_to_bot(bot.id)
        for user in users:
            u_data = user.data or {}
            new_auth_notifications_sent = u_data["auth_notifications_sent"]
            new_auth_notifications_sent.pop(data.bot_id, None)
            u_data["auth_notifications_sent"] = new_auth_notifications_sent
            user.data = u_data
            await user_repo.update_user_data(user.tg_id, u_data)

    if authed:
        await repo.delete_qr(data.bot_id)

    logger.info(f"Authentication state updated for WhatsApp bot: {data.bot_id}")

    return WhatsAppBotResponse(
        success=True,
        message="Authentication state updated successfully",
        data={"bot_id": data.bot_id, "authed": authed}
    )


@router.post("/whatsapp/notify", response_model=WhatsAppBotResponse)
async def whatsapp_bot_custom_notify(
        data: CustomNotificationRequest,
        db: AsyncSession = Depends(get_db)
):
    """Send custom notification from WhatsApp bot to Telegram users"""
    user_repo = UserRepository(db)
    bot_repo = BotRepository(db)

    try:
        # Определяем, кому отправлять уведомление
        if data.bot_id:
            users_to_notify = await user_repo.get_users_linked_to_bot(data.bot_id)
        else:
            return WhatsAppBotResponse(
                success=False,
                message="Either user_tg_id or bot_id must be provided",
                data={}
            )

        if not users_to_notify:
            logger.warning(f"No users found to notify for bot_id={data.bot_id}")
            return WhatsAppBotResponse(
                success=False,
                message="No users found to notify",
                data={"bot_id": data.bot_id}
            )

        for user in users_to_notify:
            try:
                message_text = f"**📢 Custom Notification from {data.sender_name}**\n\n{data.message}"
                if data.bot_id:
                    bot_info = await bot_repo.get_bot(data.bot_id)
                    if bot_info:
                        message_text = f"**📢 Custom Notification from Bot {bot_info.name} ({data.sender_name})**\n\n{data.message}"

                await bot_connector.bot.send_message(
                    chat_id=user.tg_id,
                    text=message_text,
                    parse_mode="Markdown"
                )
                logger.info(f"Sent custom notification to user {user.tg_id} from {data.sender_name}")
            except Exception as e:
                logger.error(f"Failed to send custom notification to user {user.tg_id}: {e}")

        return WhatsAppBotResponse(
            success=True,
            message="Custom notification sent successfully",
            data={"bot_id": data.bot_id}
        )
    except Exception as e:
        logger.error(f"Error in custom notification endpoint: {e}")
        return WhatsAppBotResponse(
            success=False,
            message=f"Internal server error: {str(e)}",
            data={}
        )
