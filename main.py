import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.logger import logger
from api.endpoints import router as api_router
from bot.services.bot_connector import bot_connector
from scripts.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    try:
        # Initialize database with default admin user
        await init_db()
        
        # Start Telegram bot
        bot_task = asyncio.create_task(bot_connector.start())
        logger.info("Application started successfully")
        
        yield
        
        # Stop Telegram bot
        bot_task.cancel()
        await bot_connector.stop()
        logger.info("Application stopped successfully")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


app = FastAPI(title="GFP Watcher-QR", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )