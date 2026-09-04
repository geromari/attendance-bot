import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from pathlib import Path

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./attendance.db')

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database with schema"""
    async with engine.begin() as conn:
        # Read and execute the initial migration
        migration_path = Path(__file__).parent / 'migrations' / '001_initial.sql'
        if migration_path.exists():
            with open(migration_path, 'r') as f:
                schema = f.read()
            # Split by semicolon and execute each statement
            for statement in schema.split(';'):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))

async def get_session() -> AsyncSession:
    """Dependency to get database session"""
    async with async_session() as session:
        yield session
