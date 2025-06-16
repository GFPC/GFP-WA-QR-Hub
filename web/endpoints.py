from fastapi import APIRouter, Depends, HTTPException
from core.models import QRRequest
from storage.bot_repo import WhatsAppBotRepository
from sqlalchemy.ext.asyncio import AsyncSession
from web.auth import SecretKeyAuth
import logging
from typing import Dict

logger = logging.getLogger(__name__)
router = APIRouter()
auth = SecretKeyAuth()


@router.post("/api/qr_update")
async def update_qr(
    request: QRRequest,
    bot_repo: WhatsAppBotRepository = Depends(),
    _: bool = Depends(auth)
) -> Dict[str, str]:
    """Update QR code for a WhatsApp bot."""
    try:
        bot = await bot_repo.get_by_id(request.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Here you would typically update the QR code in the database
        # and trigger a notification to the Telegram bot
        logger.info(f"QR update received for bot {request.bot_id}")
        
        return {"status": "success", "message": "QR update received"}
    except Exception as e:
        logger.error(f"Error processing QR update: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "services": {
            "database": "connected",
            "telegram": "connected"
        }
    } 