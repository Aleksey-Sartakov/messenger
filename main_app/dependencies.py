from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from main_app.database import async_sessionmaker_instance


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker_instance() as async_session:
        yield async_session
