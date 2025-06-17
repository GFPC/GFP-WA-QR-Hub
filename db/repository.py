from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from db.models import Bot, User, UserBotAssociation
from core.logger import logger


class BotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_bot(self, bot_id: str, name: str, description: str) -> Bot:
        bot = Bot(id=bot_id, name=name, description=description)
        self.session.add(bot)
        await self.session.commit()
        logger.info(f"Created new bot: {bot_id}")
        return bot
    
    async def get_bot(self, bot_id: str) -> Optional[Bot]:
        result = await self.session.execute(
            select(Bot).where(Bot.id == bot_id)
        )
        return result.scalar_one_or_none()
    
    async def update_qr(self, bot_id: str, qr_data: str) -> bool:
        result = await self.session.execute(
            update(Bot)
            .where(Bot.id == bot_id)
            .values(current_qr=qr_data)
        )
        await self.session.commit()
        logger.info(f"Updated QR for bot: {bot_id}")
        return result.rowcount > 0
    
    async def update_auth_state(self, bot_id: str, authed: bool) -> bool:
        result = await self.session.execute(
            update(Bot)
            .where(Bot.id == bot_id)
            .values(authed=authed)
        )
        await self.session.commit()
        logger.info(f"Updated auth state for bot {bot_id}: {authed}")
        return result.rowcount > 0
    
    async def get_unlinked_bots(self, user_id: int) -> List[Bot]:
        result = await self.session.execute(
            select(Bot)
            .outerjoin(UserBotAssociation)
            .where(UserBotAssociation.user_id.is_(None))
        )
        return list(result.scalars().all())
    
    async def link_bot_to_user(self, user_id: int, bot_id: str) -> bool:
        association = UserBotAssociation(user_id=user_id, bot_id=bot_id)
        self.session.add(association)
        try:
            await self.session.commit()
            logger.info(f"Linked bot {bot_id} to user {user_id}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to link bot {bot_id} to user {user_id}: {e}")
            return False


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, tg_id: int) -> User:
        result = await self.session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(tg_id=tg_id, data={"notifications": True})
            self.session.add(user)
            await self.session.commit()
            logger.info(f"Created new user: {tg_id}")
        
        return user
    
    async def get_user_bots(self, tg_id: int) -> List[Bot]:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.bots))
            .where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()
        return user.bots if user else []

    async def get_users_linked_to_bot(self, bot_id: str) -> List[User]:
        result = await self.session.execute(
            select(User)
            .join(User.bots)
            .where(Bot.id == bot_id)
        )
        return result.scalars().all()

    async def update_user_data(self, tg_id: int, data: dict):
        await self.session.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(data=data)
        )
        await self.session.commit()
        logger.info(f"Updated data for user: {tg_id}") 