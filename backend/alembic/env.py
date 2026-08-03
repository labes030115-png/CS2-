from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.db.database import metadata


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_path = os.environ.get("CS2_DATABASE_PATH")
if database_path:
    resolved_path = Path(database_path).expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite+pysqlite:///{resolved_path.as_posix()}",
    )

target_metadata = metadata


def run_migrations_offline() -> None:
    """Configure SQL generation without opening a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured local SQLite database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            # The PRAGMAs start SQLAlchemy's implicit transaction. Finish it
            # before Alembic inspects the connection so revision stamps are
            # committed by Alembic's own migration transaction.
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
