import os
import sys
import asyncio
import logging
from datetime import datetime

# Add project root and code directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.database.connection import SessionLocal, engine
from backend.database.models import Base, DBFile, DBMajor, DBCourse
from backend.root_path import KB_ROOT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_metadata():
    """
    Populates the database with initial metadata for Majors, Courses, and Files.
    This assumes the vector indexing (reindex_all.py) has already been run,
    so the files exist in the knowledge_base directory.
    This script registers those files into the 'files' table and sets up course/major structure.
    """
    logger.info("Starting metadata population...")
    db = SessionLocal()

    try:
        # 1. Create Majors
        # ----------------
        majors_data = [
            {"code": "AIBA", "name": "MSc in Artificial Intelligence and Business Analytics", "department": "Data Science"},
            {"code": "DS", "name": "MSc in Data Science", "department": "Data Science"},
            {"code": "ADS", "name": "MSc in Applied Data Science", "department": "Data Science"}, # Assuming ADS based on typical acronym
        ]

        for m_data in majors_data:
            existing = db.query(DBMajor).filter(DBMajor.code == m_data["code"]).first()
            if not existing:
                major = DBMajor(**m_data)
                db.add(major)
                logger.info(f"Added Major: {m_data['code']}")
            else:
                logger.info(f"Major exists: {m_data['code']}")
        db.commit()

        # 2. Create Courses
        # -----------------
        # Mapping courses to majors (Assuming AIBA for now based on typical curriculum, or DS)
        courses_data = [
            {"course_code": "CDS524", "name": "Machine Learning for Business", "major_code": "AIBA"},
            {"course_code": "CDS527", "name": "Big Data Analytics", "major_code": "AIBA"},
            # Add more if known
        ]

        for c_data in courses_data:
            existing = db.query(DBCourse).filter(DBCourse.course_code == c_data["course_code"]).first()
            if not existing:
                course = DBCourse(**c_data)
                db.add(course)
                logger.info(f"Added Course: {c_data['course_code']}")
        db.commit()

        # 3. Register Files (Scan knowledge_base and add to DBFile)
        # ---------------------------------------------------------
        # We need to map the physical files to the logical DBFile records.
        # Logic:
        # - backend/knowledge_base/public -> access_level='public', base='lingnan'
        # - backend/knowledge_base/course_CDS524 -> access_level='internal', related_course_code='CDS524'

        # Knowledge base root (runtime data under .local_data)
        kb_path = KB_ROOT

        logger.info(f"Using Knowledge Base Path: {kb_path}")

        # Scan for all course folders dynamically
        course_dirs = [d for d in os.listdir(kb_path) if d.startswith("course_") and os.path.isdir(os.path.join(kb_path, d))]

        # Add discovered courses to DB if not exist
        for d in course_dirs:
            # d is like "course_CDS524"
            code = d.replace("course_", "")
            # Check if course exists
            existing_course = db.query(DBCourse).filter(DBCourse.course_code == code).first()
            if not existing_course:
                # Add it
                # Default to AIBA major for now as per user context, name unknown so use code
                new_course = DBCourse(
                    course_code=code,
                    name=f"Course {code}",
                    major_code="AIBA"
                )
                db.add(new_course)
                logger.info(f"Added Discovered Course: {code}")
        db.commit()

        # Define rules
        dir_rules = {
            "public": {"access_level": "public", "base": "public", "file_type": "policy"},
        }
        # Add dynamic rules for courses
        for d in course_dirs:
            code = d.replace("course_", "")
            dir_rules[d] = {
                "access_level": "internal",
                "base": d,
                "related_course_code": code,
                "file_type": "course_material"
            }

        # Scan and insert
        for dir_name, rules in dir_rules.items():
            base_dir = os.path.join(kb_path, dir_name)
            logger.info(f"Scanning directory: {base_dir}")

            if not os.path.exists(base_dir):
                logger.warning(f"Directory not found: {base_dir}")
                continue

            for root, dirs, filenames in os.walk(base_dir):
                if 'pieces' in dirs:
                    dirs.remove('pieces')

                logger.info(f"Scanning sub-directory: {root} - Found {len(filenames)} files")

                for f in filenames:
                    if f.endswith(('.pdf', '.pptx', '.txt', '.md', '.docx', '.doc')):
                        file_path_abs = os.path.join(root, f)
                        # Store absolute path (compatible with repo-level data root)
                        existing_file = db.query(DBFile).filter(DBFile.file_path == file_path_abs).first()

                        if not existing_file:
                            new_file = DBFile(
                                file_name=f,
                                file_path=file_path_abs,
                                file_size=str(os.path.getsize(file_path_abs)),
                                file_type=rules.get("file_type", "unknown"),
                                access_level=rules["access_level"],
                                base=rules.get("base", "lingnan"),
                                related_course_code=rules.get("related_course_code"),
                                uploader_id=1, # Assign to the Admin user (User ID 1) we assume you just created
                                uploaded_at=datetime.now()
                            )
                            db.add(new_file)
                            logger.info(f"Registered File: {f} -> {rules['access_level']}")
                        else:
                            logger.info(f"File already registered: {f}")
        db.commit()
        logger.info("Metadata population complete!")

    except Exception as e:
        logger.error(f"Error populating metadata: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_metadata()
