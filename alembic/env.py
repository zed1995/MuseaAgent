"""Alembic environment configuration.

Reads the database URL from application settings (env vars / .env file).
"""
from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.core.config import get_settings
from backend.models.base import Base

target_metadata = Base.metadata

config = context.config

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database.url)


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


run_migrations_online()
