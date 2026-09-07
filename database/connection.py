import os

from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres@localhost:5432/ps02"
)

engine = create_engine(
    DATABASE_URL,
    echo=False
)