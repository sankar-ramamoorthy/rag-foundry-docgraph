from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text, MetaData
from alembic import context
import sys
import os

# Add src folder to sys.path so we can import ingestion_service
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

# Import your Base
from ingestion_service.src.core.models import Base

# Alembic Config object
config = context.config
# Allow overriding DB URL via env var or -x db_url
db_url = context.get_x_argument(as_dictionary=True).get("db_url") or os.environ.get(
    "DATABASE_URL"
)

if not db_url:
    raise RuntimeError("DATABASE_URL is not set and no -x db_url was provided")

config.set_main_option("sqlalchemy.url", db_url)
# Set up Python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic autogenerate support: use the metadata of your Base
target_metadata: MetaData = Base.metadata  # type: ignore[attr-defined]


# -----------------------------
# Offline migrations
# -----------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="ingestion_service",
    )
    with context.begin_transaction():
        context.run_migrations()


# -----------------------------
# Online migrations
# -----------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Use a transaction context for the connection
    with connectable.begin() as connection:
        # Ensure schema exists
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ingestion_service;"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="ingestion_service",
            include_schemas=True,
        )
        context.run_migrations()


# -----------------------------
# Run the appropriate migration mode
# -----------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
