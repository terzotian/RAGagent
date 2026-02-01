CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    gender TEXT NOT NULL CHECK(gender IN ('Male', 'Female')),
    identity TEXT NOT NULL CHECK(identity IN ('Student', 'Teacher')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
