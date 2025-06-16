from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[User]:
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def update(self, user_id: int, **kwargs) -> Optional[User]:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_by_telegram_id(user_id)

    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_telegram_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False 