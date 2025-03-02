from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _app_init():
    from ScoRHEgami.common.settings import AppSettings
    from ScoRHEgami.common.models.orm import Base

    app_settings = AppSettings()
    config.set_main_option("sqlalchemy.url", str(app_settings.DB_URI))
    config.set_main_option("db_schema", str(app_settings.DB_SCHEMA))

    return Base.metadata


target_metadata = _app_init()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
