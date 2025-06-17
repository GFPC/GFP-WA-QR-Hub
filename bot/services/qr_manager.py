from typing import Optional
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import FSInputFile, InputMediaPhoto
import qrcode
import tempfile
import os

from db.repository import BotRepository, UserRepository
from core.config import settings
from core.logger import logger

# Initialize Redis client if URL is provided
redis_client: Optional[redis.Redis] = None
if settings.REDIS_URL:
    redis_client = redis.from_url(settings.REDIS_URL)


class QRManager:
    @staticmethod
    async def get_last_qr_message(user_id: int, bot_id: str) -> Optional[int]:
        """Get the last QR message ID from cache"""
        if not redis_client:
            return None
        
        key = f"last_qr_msg:{user_id}:{bot_id}"
        msg_id = await redis_client.get(key)
        return int(msg_id) if msg_id else None
    
    @staticmethod
    async def set_last_qr_message(user_id: int, bot_id: str, message_id: int):
        """Cache the last QR message ID"""
        if not redis_client:
            return
        
        key = f"last_qr_msg:{user_id}:{bot_id}"
        await redis_client.set(key, message_id, ex=86400)  # 24 hours TTL
    
    @staticmethod
    async def notify_subscribed_users(bot_id: str, db: AsyncSession, tg_bot):
        """Notify all users subscribed to the bot about QR update"""
        bot_repo = BotRepository(db)
        user_repo = UserRepository(db)
        bot = await bot_repo.get_bot(bot_id)
        if not bot or not bot.current_qr:
            logger.error(f"No QR data found for bot {bot_id}")
            return
        users = await user_repo.get_users_linked_to_bot(bot_id)
        for user in users:
            try:
                data = user.data or {}
                qr_messages = data.get("qr_messages", {})
                msg_id = qr_messages.get(bot_id)
                # Генерируем QR-картинку
                qr_data = bot.current_qr.split(',')[0] if ',' in bot.current_qr else bot.current_qr
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_data)
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="black", back_color="white")
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    qr_image.save(temp_file.name)
                    temp_file_path = temp_file.name
                try:
                    qr_file = FSInputFile(temp_file_path)
                    caption = f"🔄 QR code for {bot.name}\n\nScan this QR code with WhatsApp to authenticate your bot."
                    if msg_id:
                        # Обновляем существующее сообщение
                        await tg_bot.edit_message_media(
                            chat_id=user.tg_id,
                            message_id=msg_id,
                            media=InputMediaPhoto(media=qr_file, caption=caption)
                        )
                    else:
                        # Отправляем новое сообщение
                        sent = await tg_bot.send_photo(
                            chat_id=user.tg_id,
                            photo=qr_file,
                            caption=caption
                        )
                        qr_messages[bot_id] = sent.message_id
                        data["qr_messages"] = qr_messages
                        user.data = data
                        await user_repo.update_user_data(user.tg_id, data)
                finally:
                    os.unlink(temp_file_path)
                logger.info(f"Notified user {user.tg_id} about QR update for bot {bot_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {user.tg_id} about QR update: {e}") 