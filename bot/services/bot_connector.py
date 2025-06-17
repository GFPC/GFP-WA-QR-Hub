from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import logger
from bot.handlers import commands, callbacks
from bot.middlewares.database import DatabaseMiddleware


class BotConnector:
    def __init__(self):
        self.bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Register middleware
        self.dp.update.middleware(DatabaseMiddleware())
        
        # Register handlers
        self.dp.include_router(commands.router)
        self.dp.include_router(callbacks.router)
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Telegram bot...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("Stopping Telegram bot...")
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"Error while stopping bot: {e}")
            raise


# Create global bot instance
bot_connector = BotConnector() 