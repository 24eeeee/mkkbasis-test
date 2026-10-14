from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from ..core.config import settings


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
