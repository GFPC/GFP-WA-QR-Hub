import asyncio
import logging
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import get_settings
from web.endpoints import router as web_router
from telegram.handlers import router as telegram_router
from telegram.qr_manager import QRManager
from storage.bot_repo import WhatsAppBotRepository
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(title="WhatsApp QR Manager")
app.include_router(web_router)

# Initialize database
engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Initialize Telegram bot
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
dp.include_router(telegram_router)

# Initialize QR manager
bot_repo = WhatsAppBotRepository(async_session())
qr_manager = QRManager(bot, bot_repo)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Start Telegram bot
        await dp.start_polling(bot)
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        # Stop Telegram bot
        await bot.session.close()
        logger.info("Telegram bot stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping Telegram bot: {str(e)}")


async def cleanup_task():
    """Periodic cleanup task."""
    while True:
        try:
            await qr_manager.cleanup_old_messages()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying


if __name__ == "__main__":
    # Start cleanup task
    asyncio.create_task(cleanup_task())
    
    # Start HTTP server
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
