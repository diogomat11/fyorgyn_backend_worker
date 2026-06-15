# database.py — Conexão com o banco Supabase PostgreSQL
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# NullPool para compatibilidade com Supabase (sem manter conexões ociosas)
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency que fornece uma sessão do banco e garante fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
