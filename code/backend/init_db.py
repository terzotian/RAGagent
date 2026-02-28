import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.models import Base, DBMajor, DBCourse, DBUser
from backend.database.connection import DATABASE_URL

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def init_db():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    print("Resetting database...")
    # Drop all tables to ensure clean slate with new schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("Populating Majors...")
    majors = [
        DBMajor(code="AIBA", name="MSc in Artificial Intelligence and Business Analytics", department="Data Science"),
        DBMajor(code="DS", name="MSc in Data Science", department="Data Science"),
        DBMajor(code="ADS", name="MSc in Applied Data Science", department="Data Science")
    ]

    for m in majors:
        session.merge(m)

    print("Populating Courses...")
    courses = [
        # AIBA Courses
        DBCourse(course_code="CDS524", name="Machine Learning for Business", major_code="AIBA"),
        DBCourse(course_code="CDS525", name="Practical Application of Deep Learning", major_code="AIBA"),
        DBCourse(course_code="CDS527", name="Big Data Analytics", major_code="AIBA"),
        DBCourse(course_code="CDS540", name="Computer Vision", major_code="AIBA"),
        DBCourse(course_code="CDS547", name="Intro to Large Language Models", major_code="AIBA"),
    ]

    for c in courses:
        session.merge(c)

    print("Populating Default User...")
    existing_admin = session.query(DBUser).filter(DBUser.account == "admin").first()
    if not existing_admin:
        admin_user = DBUser(
            account="admin",
            password_hash=pwd_context.hash("admin"),
            nickname="Admin User",
            role="admin",
            major_code="AIBA",
        )
        session.add(admin_user)

    session.commit()
    print("Database initialization complete.")
    session.close()

if __name__ == "__main__":
    init_db()
