import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/trading_reports")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_connection():
    """
    Context manager for database connection.
    Returns a SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_encrypted_credential(credential_id: str) -> str | None:
    """
    Fetch encrypted data for a given credential_id.
    """
    with get_db_connection() as db:
        result = db.execute(
            text("SELECT encrypted_data FROM credentials WHERE id = :id"),
            {"id": credential_id}
        ).fetchone()
        
        if result:
            return result[0]
        return None
