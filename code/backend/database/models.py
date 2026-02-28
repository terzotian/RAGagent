from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, func, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class DBSession(Base):
    __tablename__ = "sessions"
    session_id = Column(String(28), primary_key=True)
    user_id = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_activity = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class DBQuestion(Base):
    __tablename__ = "questions"
    session_id = Column(String(28), primary_key=True)
    question_id = Column(String(28), primary_key=True)
    previous_questions = Column(JSON)
    current_question = Column(Text)
    rewritten_question = Column(Text, nullable=True) # New: Context-aware rewritten query
    search_scope = Column(JSON, nullable=True) # New: List of collections searched
    answer = Column(Text)
    references = Column(JSON)
    follow_up_questions = Column(JSON, nullable=True) # New: Suggested follow-up questions
    rating = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

class DBMajor(Base):
    __tablename__ = "majors"
    code = Column(String(20), primary_key=True)  # AIBA, DS, ADS
    name = Column(String(100), nullable=False)   # MSc in AIBA
    department = Column(String(100), nullable=False, default="Data Science")

class DBCourse(Base):
    __tablename__ = "courses"
    course_code = Column(String(20), primary_key=True) # CDS524
    name = Column(String(100), nullable=False)
    major_code = Column(String(20), nullable=False) # FK -> majors.code

class DBFile(Base):
    __tablename__ = "files"
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(String(28), nullable=True)
    file_type = Column(String(20), nullable=False) # policy, course_ppt, course_rubric, student_assignment
    access_level = Column(String(20), nullable=False, default='internal') # public, internal, private

    # Context
    base = Column(String(28), nullable=False, default="lingnan") # Legacy support
    related_course_code = Column(String(20), nullable=True) # FK -> courses.course_code

    # Ownership
    uploader_id = Column(Integer, nullable=True) # FK -> users.user_id

    uploaded_at = Column(TIMESTAMP, server_default=func.now())
    description = Column(Text, nullable=True)

class DBUser(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False, default='student') # student, teacher, admin
    major_code = Column(String(20), nullable=True) # AIBA, DS...
    avatar_path = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class DBItem(Base):
    __tablename__ = "items"
    id = Column(String(64), primary_key=True)
    embedding = Column(Vector(768)) # Vertex AI text-embedding-004 uses 768 dimensions
    document = Column(Text)
    metadata_ = Column(JSON) # 'metadata' is reserved in sqlalchemy
    created_at = Column(TIMESTAMP, server_default=func.now())
