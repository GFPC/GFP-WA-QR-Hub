from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from core.config import settings
from core.logger import logger


# Database setup
engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def verify_secret_key(request: Request):
    if request.headers.get('X-Auth-Key') != settings.API_SECRET.get_secret_value():
        logger.warning(f"Invalid auth key attempt from {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid auth key") 