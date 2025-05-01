import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
from sqlalchemy.pool import NullPool

encoded_password = urllib.parse.quote_plus(settings.password)

DATABASE_URL = f"postgresql+psycopg2://{settings.username}:{settings.password}@{settings.host}:{settings.port}/{settings.dbname}"
print(f"Connecting to database at {settings.host} as {settings.username}")

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable SQLAlchemy client-side pooling
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
