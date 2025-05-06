import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context
from app.db.database import Base
from app.db.models.user import User
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.widget import WidgetSession
from app.db.models.agent import Agent
from app.db.models.chat import ChatMessage
from app.db.models.organization import Organization  # MJ: Include Organization Model
from dotenv import load_dotenv
import os

# MJ: Load environment variables from .env file
load_dotenv()

config = context.config

# MJ: Interpret the config file for logging
fileConfig(config.config_file_name)

# MJ: Set up target metadata for Alembic
target_metadata = Base.metadata

# MJ: Read the database URL securely from environment variables
DB_URL = os.getenv("DATABASE_URL")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    if not DB_URL:
        raise ValueError("DATABASE_URL not set in environment variables.")

    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode."""
    if not DB_URL:
        raise ValueError("DATABASE_URL not set in environment variables.")

    connectable = create_async_engine(DB_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
