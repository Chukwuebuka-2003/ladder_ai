import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Session maker for creating sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# Base class for declarative models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    """
    Provide a SQLAlchemy Session for use as a FastAPI dependency.
    
    Yields a new SessionLocal() instance for the caller (typically used with FastAPI's `Depends`)
    and ensures the session is closed after use.
    
    Returns:
        sqlalchemy.orm.Session: a database session instance (yielded).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
