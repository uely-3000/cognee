import asyncio
import json as _json
import os
import ssl as _ssl

from alembic import context
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from cognee.infrastructure.databases.relational import get_relational_engine, Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _migration_connect_args():
    """Build connect_args for the Alembic migration engine.

    Reads DATABASE_CONNECT_ARGS (JSON) for driver-level args like
    statement_cache_size, and DATABASE_SSL_CA_CERT (file path) to
    create an ssl.SSLContext for verified TLS connections.
    """
    args = {}
    raw = os.environ.get("DATABASE_CONNECT_ARGS", "")
    if raw:
        try:
            parsed = _json.loads(raw)
            if isinstance(parsed, dict):
                args = parsed
        except _json.JSONDecodeError:
            pass

    ca_cert = os.environ.get("DATABASE_SSL_CA_CERT")
    if ca_cert and "ssl" not in args:
        ctx = _ssl.create_default_context(cafile=ca_cert)
        args["ssl"] = ctx

    return args


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an Engine and associate a connection with the context."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_migration_connect_args(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


db_engine = get_relational_engine()

print("Using database:", db_engine.db_uri)
db_uri = (
    db_engine.db_uri
    if isinstance(db_engine.db_uri, str)
    else db_engine.db_uri.render_as_string(hide_password=False)
)

config.set_section_option(
    config.config_ini_section,
    "SQLALCHEMY_DATABASE_URI",
    db_uri,
)


if context.is_offline_mode():
    print("OFFLINE MODE")
    run_migrations_offline()
else:
    run_migrations_online()
