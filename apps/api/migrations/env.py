import os
from alembic import context
from sqlalchemy import create_engine

URL = os.environ.get(
    "CLAIMGUARD_DATABASE_URL",
    "postgresql+psycopg://claimguard:claimguard_dev@localhost:55432/claimguard",
)


def run_migrations_online() -> None:
    engine = create_engine(URL)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()