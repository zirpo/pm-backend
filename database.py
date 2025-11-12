import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check if we're in a test environment
IS_TEST = os.getenv('TEST_ENV', '').lower() in ('test', 'testing')

if IS_TEST:
    # Use SQLite for testing
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
    if DATABASE_URL.startswith('sqlite'):
        # Convert to async SQLite URL
        ASYNC_DATABASE_URL = DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///')
    else:
        # Handle other test database URLs
        if DATABASE_URL.startswith('postgresql+psycopg2://'):
            ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
        else:
            ASYNC_DATABASE_URL = DATABASE_URL
else:
    # Get PostgreSQL connection URL from environment for production
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password@localhost:5432/pm_backend')
    # For async engine, we need to replace psycopg2 with asyncpg
    ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')

# Create async engine with appropriate echo level (less verbose for tests)
engine = create_async_engine(ASYNC_DATABASE_URL, echo=not IS_TEST)

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