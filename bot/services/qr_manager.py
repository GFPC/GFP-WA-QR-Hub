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
        """Notify all users subscribed to the bot about QR update (text notification if not authed)"""
        bot_repo = BotRepository(db)
        user_repo = UserRepository(db)
        bot = await bot_repo.get_bot(bot_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found for notification.")
            return

        users = await user_repo.get_users_linked_to_bot(bot_id)
        for user in users:
            data = user.data or {}
            auth_notifications_sent = data.get("auth_notifications_sent", {})

            if not bot.authed:
                # Бот не авторизован, отправляем текстовое уведомление, если еще не отправляли
                if not auth_notifications_sent.get(bot_id, False):
                    await tg_bot.send_message(
                        chat_id=user.tg_id,
                        text=f"⚠️ Bot {bot.name} requires authentication! Please use the 'Auth QR' button if you need to scan the QR code."
                    )
                    auth_notifications_sent[bot_id] = True
                    data["auth_notifications_sent"] = auth_notifications_sent
                    user.data = data
                    await user_repo.update_user_data(user.tg_id, data)
                    logger.info(f"Sent auth required notification to user {user.tg_id} for bot {bot_id}.")
                qr_code_message = data.get("qr_messages", {}).get(bot_id, None)

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(bot.current_qr)  # <-- Здесь передаем чистую строку из БД
                qr.make(fit=True)

                # Создаем изображение QR кода
                qr_image = qr.make_image(fill_color="black", back_color="white")

                # Сохраняем во временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    qr_image.save(temp_file.name)
                    temp_file_path = temp_file.name

                try:
                    # Создаем FSInputFile из временного файла
                    qr_file = FSInputFile(temp_file_path)

                    # Обновляем qr код на сообщении с id

                    print("Trying to edit message: ", qr_code_message, "in chat: ", user.tg_id,data)
                    if qr_code_message:
                        await tg_bot.edit_message_media(
                            chat_id=user.tg_id,
                            message_id=qr_code_message,
                            media=InputMediaPhoto(media=qr_file,
                                                  caption=f"🔐 QR Code for {bot.name}\n\nScan this QR code with WhatsApp to authenticate your bot.")
                        )

                finally:
                    # Удаляем временный файл
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.error(f"Error deleting temporary file: {e}")
            else:
                # Бот авторизован, убедимся, что флаг сброшен
                if auth_notifications_sent.get(bot_id, False):
                    auth_notifications_sent[bot_id] = False
                    data["auth_notifications_sent"] = auth_notifications_sent
                    user.data = data
                    await user_repo.update_user_data(user.tg_id, data)
                    logger.info(f"Reset auth required notification flag for user {user.tg_id}, bot {bot_id}.")

    @staticmethod
    async def notify_auth_success(bot_id: str, db: AsyncSession, tg_bot):
        """Notify users that the bot has been successfully authenticated"""
        bot_repo = BotRepository(db)
        user_repo = UserRepository(db)
        bot = await bot_repo.get_bot(bot_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found")
            return
        users = await user_repo.get_users_linked_to_bot(bot_id)
        for user in users:
            try:
                data = user.data or {}
                qr_messages = data.get("qr_messages", {})
                msg_id = qr_messages.get(bot_id)
                logger.info(
                    f"Attempting to delete QR message for user {user.tg_id}, bot {bot_id}. Message ID found: {msg_id}")

                if msg_id:
                    try:
                        # Удаляем сообщение с QR-кодом
                        await tg_bot.delete_message(chat_id=user.tg_id, message_id=msg_id)
                        logger.info(f"Successfully deleted QR message {msg_id} for user {user.tg_id}, bot {bot_id}.")
                        # Удаляем message_id из данных пользователя
                        qr_messages.pop(bot_id, None)
                        data["qr_messages"] = qr_messages
                        user.data = data
                        await user_repo.update_user_data(user.tg_id, data)
                    except Exception as delete_e:
                        logger.error(
                            f"Error deleting QR message {msg_id} for user {user.tg_id}, bot {bot_id}: {delete_e}")
                else:
                    logger.info(
                        f"No QR message ID found in user data for user {user.tg_id}, bot {bot_id}. Message not deleted.")

                # Отправляем уведомление об успешной авторизации
                await tg_bot.send_message(
                    chat_id=user.tg_id,
                    text=f"✅ Bot {bot.name} has been successfully authenticated!"
                )
                logger.info(f"Notified user {user.tg_id} about successful authentication for bot {bot_id}")

                # Сбрасываем флаг уведомления о необходимости авторизации
                auth_notifications_sent = data.get("auth_notifications_sent", {})
                if auth_notifications_sent.get(bot_id, False):
                    auth_notifications_sent[bot_id] = False
                    data["auth_notifications_sent"] = auth_notifications_sent
                    user.data = data
                    await user_repo.update_user_data(user.tg_id, data)
                    logger.info(
                        f"Reset auth required notification flag for user {user.tg_id}, bot {bot_id} after successful auth.")

            except Exception as e:
                logger.error(f"Failed to notify user {user.tg_id} about authentication success: {e}")

    @staticmethod
    async def notify_deauth_success(bot_id: str, db: AsyncSession, tg_bot):
        bot_repo = BotRepository(db)
        user_repo = UserRepository(db)
        bot = await bot_repo.get_bot(bot_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found")
            return
        users = await user_repo.get_users_linked_to_bot(bot_id)
        for user in users:
            try:
                data = user.data or {}
                qr_messages = data.get("qr_messages", {})
                msg_id = qr_messages.get(bot_id)
                logger.info(
                    f"Attempting to delete QR message for user {user.tg_id}, bot {bot_id}. Message ID found: {msg_id}")

                if msg_id:
                    try:
                        # Удаляем сообщение с QR-кодом
                        await tg_bot.delete_message(chat_id=user.tg_id, message_id=msg_id)
                        logger.info(f"Successfully deleted QR message {msg_id} for user {user.tg_id}, bot {bot_id}.")
                        # Удаляем message_id из данных пользователя
                        qr_messages.pop(bot_id, None)
                        data["qr_messages"] = qr_messages
                        user.data = data
                        await user_repo.update_user_data(user.tg_id, data)
                    except Exception as delete_e:
                        logger.error(
                            f"Error deleting QR message {msg_id} for user {user.tg_id}, bot {bot_id}: {delete_e}")
                else:
                    logger.info(
                        f"No QR message ID found in user data for user {user.tg_id}, bot {bot_id}. Message not deleted.")

                # Отправляем уведомление об успешной авторизации
                await tg_bot.send_message(
                    chat_id=user.tg_id,
                    text=f"🔴 Bot {bot.name} has been successfully deauthenticated!"
                )
                logger.info(f"Notified user {user.tg_id} about successful deauthentication for bot {bot_id}")

                # Сбрасываем флаг уведомления о необходимости авторизации
                auth_notifications_sent = data.get("deauth_notifications_sent", {})
                if auth_notifications_sent.get(bot_id, False):
                    auth_notifications_sent[bot_id] = False
                    data["deauth_notifications_sent"] = auth_notifications_sent
                    user.data = data
                    await user_repo.update_user_data(user.tg_id, data)
                    logger.info(
                        f"Reset auth required notification flag for user {user.tg_id}, bot {bot_id} after successful deauth.")

            except Exception as e:
                logger.error(f"Failed to notify user {user.tg_id} about deauthentication success: {e}")
