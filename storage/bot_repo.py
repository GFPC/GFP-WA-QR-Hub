from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.models import WhatsAppBot
from datetime import datetime


class WhatsAppBotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, bot: WhatsAppBot) -> WhatsAppBot:
        self.session.add(bot)
        await self.session.commit()
        await self.session.refresh(bot)
        return bot

    async def get_by_id(self, bot_id: str) -> Optional[WhatsAppBot]:
        result = await self.session.execute(
            select(WhatsAppBot).where(WhatsAppBot.id == bot_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> List[WhatsAppBot]:
        result = await self.session.execute(
            select(WhatsAppBot).where(WhatsAppBot.user_id == user_id)
        )
        return result.scalars().all()

    async def update_qr_info(self, bot_id: str, message_id: int) -> Optional[WhatsAppBot]:
        await self.session.execute(
            update(WhatsAppBot)
            .where(WhatsAppBot.id == bot_id)
            .values(
                last_qr_message_id=message_id,
                last_qr_update=datetime.utcnow()
            )
        )
        await self.session.commit()
        return await self.get_by_id(bot_id)

    async def delete(self, bot_id: str) -> bool:
        bot = await self.get_by_id(bot_id)
        if bot:
            await self.session.delete(bot)
            await self.session.commit()
            return True
        return False 