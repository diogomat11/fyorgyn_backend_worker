# database.py — Conexão com o banco Supabase PostgreSQL
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load .env from backend/ if not found locally
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.ourddwzetcbdjnbvamgj.supabase.co")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Prefer DATABASE_URL when explicitly set: enables the Supabase POOLER (IPv4),
# needed in clouds like Render where the direct host db.*.supabase.co is
# IPv6-only ("Network is unreachable"). Force port 5432 (session mode), safer
# for SQLAlchemy ORM. connect_args already handles pooler compatibility
# (prepare_threshold=None). Falls back to direct SUPABASE_DB_* construction.
_DATABASE_URL_ENV = os.getenv("DATABASE_URL", "").strip()
if _DATABASE_URL_ENV:
    DATABASE_URL = _DATABASE_URL_ENV.replace(":6543", ":5432")
elif DB_HOST and "supabase.co" in DB_HOST and DB_PASSWORD:
    DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    use_native_hstore=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={
        "prepare_threshold": None,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
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
