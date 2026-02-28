import sys
import os
from sqlalchemy import create_engine, text

# Add code/ to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../code"))

# Import engine. This will load .env internally.
try:
    from backend.database.connection import engine
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback if relative import fails or .env not loaded correctly
    # But let's try to load .env explicitly if needed
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../code/backend/.env"))
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in env.")
        sys.exit(1)
    engine = create_engine(db_url)

def migrate():
    print(f"Connecting to DB...")
    with engine.connect() as conn:
        # Check if table exists first
        result = conn.execute(text("SELECT to_regclass('public.questions')"))
        if not result.scalar():
            print("Table 'questions' does not exist. Skipping migration (tables will be created on startup).")
            return

        # Check if columns exist in 'questions' table
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='questions'"))
        columns = [row[0] for row in result]
        
        print(f"Existing columns: {columns}")
        
        new_columns = {
            "rewritten_question": "TEXT",
            "search_scope": "JSON",
            "follow_up_questions": "JSON"
        }
        
        for col, type_ in new_columns.items():
            if col not in columns:
                print(f"Adding column {col}...")
                conn.execute(text(f"ALTER TABLE questions ADD COLUMN {col} {type_}"))
                conn.commit()
                print(f"Column {col} added.")
            else:
                print(f"Column {col} already exists.")

if __name__ == "__main__":
    try:
        migrate()
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")
