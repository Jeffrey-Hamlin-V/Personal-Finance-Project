"""
Database Initialization & Connection Management
Demonstrates: Connection pooling, session management, migration strategy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator

from .models import Base

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./finance_intel.db"  # Default to SQLite for development
)

# Production-ready connection pool settings
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Max 10 connections in pool
    max_overflow=20,  # Allow 20 additional connections if pool is full
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_database():
    """
    Initialize database - create all tables
    Called during app startup or migrations
    """
    print("🔧 Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes
    Provides database session with automatic cleanup
    
    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    Use in background jobs or scripts
    
    Usage:
        with get_db_context() as db:
            db.query(Transaction).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def reset_database():
    """
    WARNING: Drops all tables and recreates them
    Only use in development!
    """
    print("⚠️  WARNING: Resetting database (all data will be lost)")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Database reset complete")


if __name__ == "__main__":
    # Run this script directly to initialize database
    init_database()