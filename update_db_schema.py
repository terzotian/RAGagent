from sqlalchemy import create_engine, text

DATABASE_URL = "mysql+mysqlconnector://root:TTZZ3388@localhost:3306/LURAG"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if user_id column exists in sessions table
    result = conn.execute(text("SHOW COLUMNS FROM sessions LIKE 'user_id'"))
    if not result.fetchone():
        print("Adding user_id column to sessions table...")
        conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id INT NULL"))
        conn.execute(text("ALTER TABLE sessions ADD CONSTRAINT fk_sessions_users FOREIGN KEY (user_id) REFERENCES users(user_id)"))
        conn.commit()
        print("Column added successfully.")
    else:
        print("user_id column already exists.")

    # Check if title column exists in sessions table (optional but good for history)
    result = conn.execute(text("SHOW COLUMNS FROM sessions LIKE 'title'"))
    if not result.fetchone():
        print("Adding title column to sessions table...")
        conn.execute(text("ALTER TABLE sessions ADD COLUMN title VARCHAR(255) NULL"))
        conn.commit()
        print("Column added successfully.")
    else:
        print("title column already exists.")
