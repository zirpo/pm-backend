import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get PostgreSQL connection URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password@localhost:5432/pm_backend')

# For async engine, we need to replace psycopg2 with asyncpg
ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')

# Create async engine for PostgreSQL
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create declarative base
Base = declarative_base()

# Async dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_db_and_tables():
    """Create database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)