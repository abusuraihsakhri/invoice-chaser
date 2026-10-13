import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger("invoice_chaser.database")

def create_resilient_engine():
    db_url = settings.database_url
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(db_url, connect_args=connect_args)
    
    try:
        # Attempt to create Postgres engine with pool pre-ping
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection
        with engine.connect() as conn:
            pass
        return engine
    except Exception as exc:
        if settings.environment.lower() not in ("development", "test"):
            # Never silently switch production tenants to an unrelated local database.
            raise RuntimeError("Configured production database is unavailable") from exc
        logger.warning("Configured database is unavailable; using development SQLite fallback")
        return create_engine("sqlite:///./invoice_chaser.db", connect_args={"check_same_thread": False})

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

