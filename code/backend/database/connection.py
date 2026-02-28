import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base
from dotenv import load_dotenv

# Load environment variables from .env file
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# Database Configuration
# All environments use PostgreSQL (local Docker / Cloud SQL)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[FATAL] DATABASE_URL is not set. Please configure PostgreSQL connection in .env or environment variables.")
    print("  Example: DATABASE_URL=postgresql://postgres:password@localhost:5433/lurag")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
