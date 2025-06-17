import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from db.models import Base, User
from core.config import settings
from core.logger import logger


async def init_db():
    """Initialize database with tables and default admin user"""
    engine = create_async_engine(settings.DATABASE_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.tg_id == 963890854)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            # Create admin user
            admin = User(
                tg_id=963890854,
                data={
                    "notifications": True,
                    "is_admin": True,
                    "created_by": "system"
                }
            )
            session.add(admin)
            await session.commit()
            logger.info("Created default admin user with tg_id=963890854")
        else:
            logger.info("Admin user already exists")


if __name__ == "__main__":
    asyncio.run(init_db()) 