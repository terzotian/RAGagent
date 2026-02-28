import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.database.connection import DATABASE_URL
from backend.database.models import DBFile, DBMajor, DBCourse

def check_content():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    print(f"Checking database at: {DATABASE_URL}")

    # 1. Check Majors
    majors = session.query(DBMajor).all()
    print(f"\nMajors ({len(majors)}):")
    for m in majors:
        print(f" - {m.code}: {m.name}")

    # 2. Check Courses
    courses = session.query(DBCourse).all()
    print(f"\nCourses ({len(courses)}):")
    for c in courses:
        print(f" - {c.course_code}: {c.name} ({c.major_code})")

    # 3. Check Policies
    policies = session.query(DBFile).filter(DBFile.file_type == 'policy').all()
    print(f"\nPolicies ({len(policies)}):")
    for p in policies[:5]: # Show first 5
        print(f" - {p.file_name} (Size: {p.file_size})")
    if len(policies) > 5:
        print(f" ... and {len(policies)-5} more")

    # 4. Check Course Files
    course_files = session.query(DBFile).filter(DBFile.related_course_code.isnot(None)).all()
    print(f"\nCourse Files ({len(course_files)}):")
    for f in course_files:
        print(f" - [{f.related_course_code}] {f.file_name} ({f.file_type})")

    session.close()

if __name__ == "__main__":
    check_content()
