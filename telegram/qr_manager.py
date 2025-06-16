from aiogram import Bot
from storage.bot_repo import WhatsAppBotRepository
from core.models import QRUpdate
import logging
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class QRManager:
    def __init__(self, bot: Bot, bot_repo: WhatsAppBotRepository):
        self.bot = bot
        self.bot_repo = bot_repo
        self.qr_update_tasks: Dict[str, asyncio.Task] = {}

    async def handle_qr_update(self, qr_update: QRUpdate):
        """Handle incoming QR update."""
        try:
            bot = await self.bot_repo.get_by_id(qr_update.bot_id)
            if not bot or not bot.is_active:
                logger.info(f"Bot {qr_update.bot_id} not found or inactive")
                return

            # Cancel existing update task if any
            if qr_update.bot_id in self.qr_update_tasks:
                self.qr_update_tasks[qr_update.bot_id].cancel()
                try:
                    await self.qr_update_tasks[qr_update.bot_id]
                except asyncio.CancelledError:
                    pass

            # Create new update task
            self.qr_update_tasks[qr_update.bot_id] = asyncio.create_task(
                self._send_qr_update(qr_update)
            )

        except Exception as e:
            logger.error(f"Error handling QR update: {str(e)}")

    async def _send_qr_update(self, qr_update: QRUpdate):
        """Send QR update to Telegram chat."""
        try:
            bot = await self.bot_repo.get_by_id(qr_update.bot_id)
            if not bot:
                return

            message_text = (
                f"🔄 New QR Code Update\n"
                f"Bot ID: {qr_update.bot_id}\n"
                f"Time: {qr_update.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if bot.last_qr_message_id:
                # Edit existing message
                await self.bot.edit_message_text(
                    chat_id=bot.user_id,
                    message_id=bot.last_qr_message_id,
                    text=message_text
                )
            else:
                # Send new message
                message = await self.bot.send_message(
                    chat_id=bot.user_id,
                    text=message_text
                )
                await self.bot_repo.update_qr_info(
                    qr_update.bot_id,
                    message.message_id
                )

            # Schedule automatic update after 2 minutes
            await asyncio.sleep(120)
            await self._send_qr_update(qr_update)

        except Exception as e:
            logger.error(f"Error sending QR update: {str(e)}")

    async def cleanup_old_messages(self):
        """Clean up old QR messages."""
        try:
            bots = await self.bot_repo.get_all()
            for bot in bots:
                if bot.last_qr_update and (
                    datetime.utcnow() - bot.last_qr_update > timedelta(minutes=5)
                ):
                    if bot.last_qr_message_id:
                        try:
                            await self.bot.delete_message(
                                chat_id=bot.user_id,
                                message_id=bot.last_qr_message_id
                            )
                        except Exception as e:
                            logger.error(f"Error deleting old message: {str(e)}")
                        finally:
                            await self.bot_repo.update_qr_info(bot.id, None)

        except Exception as e:
            logger.error(f"Error cleaning up old messages: {str(e)}") 