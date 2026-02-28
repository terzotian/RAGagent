
import sys
import os
import json
from fastapi.encoders import jsonable_encoder

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../code')))

from backend.database.connection import SessionLocal
from backend.database.models import DBFile, DBCourse, DBMajor, DBUser

def verify_serialization():
    db = SessionLocal()
    try:
        # Check Users
        users = db.query(DBUser).all()
        print(f"Found {len(users)} users.")
        for user in users:
            print(f"- {user.account} (ID: {user.user_id}, Role: {user.role}, Major: {user.major_code})")
        # Test DBFile serialization (Course File)
        course_files = db.query(DBFile).filter(DBFile.related_course_code.isnot(None)).limit(1).all()
        print(f"Found {len(course_files)} course files.")
        if course_files:
            print("Attempting to serialize Course DBFile object...")
            try:
                serialized = jsonable_encoder(course_files[0])
                print("Serialization successful!")
                print(json.dumps(serialized, indent=2, default=str))
            except Exception as e:
                print(f"Serialization FAILED: {e}")

        # Test DBCourse serialization (ALL)
        courses = db.query(DBCourse).all()
        print(f"Found {len(courses)} courses.")
        for course in courses:
             print(f"- {course.course_code}: {course.name} ({course.major_code})")

        # Test DBMajor serialization
        majors = db.query(DBMajor).all()
        print(f"Found {len(majors)} majors.")
        if majors:
            print("Attempting to serialize DBMajor object...")
            try:
                serialized = jsonable_encoder(majors[0])
                print("Serialization successful!")
                print(json.dumps(serialized, indent=2, default=str))
            except Exception as e:
                print(f"Serialization FAILED: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_serialization()
