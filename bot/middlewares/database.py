from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from api.dependencies import async_session
from db.repository import UserRepository
from db.models import User

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session() as session:
            data["db"] = session
            user_repo = UserRepository(session)

            if isinstance(event, Message):
                user_id = event.from_user.id
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
            else:
                return await handler(event, data)

            existing_user = await user_repo.get_user_by_tg_id(user_id)
            
            logger.debug(f"Middleware: Processing user_id={user_id}, existing_user_found={existing_user is not None}")

            if not existing_user:
                if isinstance(event, Message):
                    await event.answer("🚫 Access Denied: This is a closed bot. Please contact an administrator to get access.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Access Denied: This is a closed bot.", show_alert=True)
                return
            
            return await handler(event, data) 