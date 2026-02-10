
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.main import DATABASE_URL, DBUser, DBCourse, DBFile

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- Users ---")
users = db.query(DBUser).all()
for u in users:
    print(f"ID: {u.user_id}, Name: {u.nickname}, Role: {u.role}, Major: {u.major_code}, Account: {u.account}")

print("\n--- Courses ---")
courses = db.query(DBCourse).all()
for c in courses:
    print(f"Code: {c.course_code}, Name: {c.name}, Major: {c.major_code}")

print("\n--- Files (Spotify) ---")
files = db.query(DBFile).filter(DBFile.file_name.like('%Spotify%')).all()
for f in files:
    print(f"ID: {f.file_id}, Name: {f.file_name}, Type: {f.file_type}, Course: {f.related_course_code}, Base: {f.base}")

db.close()
