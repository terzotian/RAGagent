import io
import mimetypes
import os
import random
import json
from urllib.parse import unquote

import uvicorn
import markdown as md_lib
import mammoth

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, HTMLResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime, timezone
from fastapi.responses import StreamingResponse

from backend.model.doc_analysis import split
from backend.model.rag_stream import stream_answer
from sqlalchemy import create_engine, Column, String, Text, Integer, TIMESTAMP, func, LargeBinary, text, orm, Index, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.mysql import JSON
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from backend.model.ques_assemble import generate_search_query
from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.root_path import PIECES_DIR, locate_path, policy_file, piece_file, piece_dir

# 数据库配置
DATABASE_URL = "mysql+mysqlconnector://root:TTZZ3388@localhost:3306/LURAG"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = orm.declarative_base()


# 数据库模型
class DBSession(Base):
    __tablename__ = "sessions"
    session_id = Column(String(28), primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_activity = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class DBQuestion(Base):
    __tablename__ = "questions"
    session_id = Column(String(28), primary_key=True)
    question_id = Column(String(28), primary_key=True)
    previous_questions = Column(JSON)
    current_question = Column(Text)
    answer = Column(Text)
    references = Column(JSON)  # 更新字段名
    rating = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())


class DBFile(Base):
    __tablename__ = "files"
    # 复合主键 (base, file_name)
    base = Column(String(28), primary_key=True, nullable=False, server_default="lingnan",
                  comment="文件来源于哪个知识库")
    file_name = Column(String(255), primary_key=True, nullable=False, comment="文件名称")
    file_description = Column(Text, comment="文件简介")
    file_path = Column(String(512), nullable=False, comment="文件在存储系统里的路径或 URL")
    file_size = Column(String(28), nullable=False, comment="文件大小")
    uploaded_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.current_timestamp(),
        comment="上传/更新文件时间"
    )
    __table_args__ = (
        # 加速按 base 查询
        Index("idx_base", "base"),
    )


class DBUser(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    identity = Column(String(20), nullable=False)
    avatar_path = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS配置
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 数据模型
class QuestionRequest(BaseModel):
    session_id: str = Field(..., min_length=6)
    question_id: str = Field(..., min_length=10)
    previous_questions: List[str] = []
    current_question: str = Field(..., min_length=1)


class QuestionResponse(BaseModel):
    session_id: str
    question_id: str
    answer: str
    references: List[Dict[str, str]]


class FeedbackRequest(BaseModel):
    session_id: str
    question_id: str
    rating: int = Field(..., ge=1, le=10)


class FeedbackResponse(BaseModel):
    session_id: str
    question_id: str


import re
from pydantic import BaseModel, Field, validator

class UserRegister(BaseModel):
    account: str = Field(..., description="Phone number (digits only)")
    password: str = Field(..., description="6-digit password")
    nickname: str = Field(..., description="Nickname (English or Chinese)")
    gender: str
    identity: str

    @validator('account')
    def validate_account(cls, v):
        if not re.match(r'^\d{11}$', v):
            raise ValueError('Account must be an 11-digit phone number')
        return v

    @validator('password')
    def validate_password(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Password must be exactly 6 digits')
        return v

    @validator('nickname')
    def validate_nickname(cls, v):
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]+$', v):
            raise ValueError('Nickname must contain only English or Chinese characters')
        return v


class UserLogin(BaseModel):
    account: str
    password: str


class UserUpdate(BaseModel):
    nickname: str = Field(..., description="Nickname")
    gender: str
    identity: str

    @validator('nickname')
    def validate_nickname(cls, v):
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]+$', v):
            raise ValueError('Nickname must contain only English or Chinese characters')
        return v

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., description="6-digit password")

    @validator('new_password')
    def validate_password(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Password must be exactly 6 digits')
        return v

@app.get("/api/v1/users/{user_id}")
async def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "account": user.account,
        "nickname": user.nickname,
        "gender": user.gender,
        "identity": user.identity,
        "avatar_path": user.avatar_path
    }

@app.put("/api/v1/users/{user_id}")
async def update_profile(user_id: int, update_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.nickname = update_data.nickname
    user.gender = update_data.gender
    user.identity = update_data.identity
    db.commit()
    db.refresh(user)
    return {
        "message": "Profile updated",
        "user": {
            "user_id": user.user_id,
            "account": user.account,
            "nickname": user.nickname,
            "gender": user.gender,
            "identity": user.identity,
            "avatar_path": user.avatar_path
        }
    }

@app.put("/api/v1/users/{user_id}/password")
async def update_password(user_id: int, password_data: PasswordUpdate, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not pwd_context.verify(password_data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    user.password_hash = pwd_context.hash(password_data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@app.post("/api/v1/users/{user_id}/avatar")
async def upload_avatar(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create avatars directory
    avatars_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"user_{user_id}_{int(datetime.now().timestamp())}{file_ext}"
    file_path = os.path.join(avatars_dir, filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Delete old avatar if exists
    if user.avatar_path:
        old_path = os.path.join(avatars_dir, os.path.basename(user.avatar_path))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except:
                pass

    # Store relative path or full URL. Storing relative filename is safer.
    # We will serve it via a static endpoint.
    user.avatar_path = filename
    db.commit()
    
    return {"message": "Avatar uploaded", "avatar_path": filename}

@app.get("/api/v1/avatars/{filename}")
async def get_avatar(filename: str):
    avatars_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
    file_path = os.path.join(avatars_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(file_path)

@app.post("/api/v1/auth/register")
async def register(user: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(DBUser).filter(DBUser.account == user.account).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Account already exists")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = DBUser(
        account=user.account,
        password_hash=hashed_password,
        nickname=user.nickname,
        gender=user.gender,
        identity=user.identity
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.user_id}


@app.post("/api/v1/auth/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.account == user.account).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid account or password")
    
    return {
        "message": "Login successful",
        "user": {
            "user_id": db_user.user_id,
            "account": db_user.account,
            "nickname": db_user.nickname,
            "gender": db_user.gender,
            "identity": db_user.identity,
            "avatar_path": db_user.avatar_path
        }
    }


# @app.post("/api/v1/questions", response_model=QuestionResponse)
# async def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
#     last_question = db.query(DBQuestion).filter(
#         DBQuestion.session_id == request.session_id
#     ).order_by(DBQuestion.created_at.desc()).first()
#
#     if last_question and (datetime.now() - last_question.created_at).total_seconds() < 1:
#         raise HTTPException(
#             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
#             detail="请求过于频繁"
#         )
#
#     db_session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
#     if not db_session:
#         db_session = DBSession(session_id=request.session_id)
#         db.add(db_session)
#         db.commit()
#
#     answer_text, references = answer(request.current_question, request.previous_questions)
#
#     db_question = DBQuestion(
#         session_id=request.session_id,
#         question_id=request.question_id,
#         previous_questions=request.previous_questions,
#         current_question=request.current_question,
#         answer=answer_text,
#         references=references,
#         rating=None
#     )
#     db.add(db_question)
#     db.commit()
#
#     return {
#         "session_id": request.session_id,
#         "question_id": request.question_id,
#         "answer": answer_text,
#         "references": references
#     }


@app.get("/api/v1/questions/stream")
async def stream_question(session_id, question_id, previous_questions, current_question: str, language="en",
                          base="lingnan"):
    previous_questions_list = json.loads(previous_questions)

    # 检索向量
    search_query, assembled_question, generate_time = await generate_search_query(current_question,
                                                                                  previous_questions_list)

    # 参考文献
    references, search_time = await search_documents(search_query,
                                                     load_segments_from_folder(input_folder=piece_dir(base=base)))

    # 生成流式回答
    async def event_generator():
        async for token in stream_answer(assembled_question, generate_time, references, search_time,
                                         target_language=language):
            yield f"data: {json.dumps({'token': token})}\n\n"

        # 发送引用文献消息，字段名为 references
        yield f"data: {json.dumps({'references': references})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/files/list")
async def list_files(
        base: str = Query("lingnan"),
        db: Session = Depends(get_db)
):
    # 只查询指定 base 下的文件
    files = (
        db.query(DBFile)
        .filter(DBFile.base == base)
        .all()
    )

    return {
        "files": [
            {
                "file_name": file.file_name,
                "file_description": file.file_description,
                "file_path": file.file_path,
                "file_size": file.file_size,
                "uploaded_at": file.uploaded_at,
                "base": file.base
            }
            for file in files
        ]
    }


@app.post("/api/v1/files")
async def upload_file(
        base: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    size_kb = len(content) / 1024
    file_size = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.1f}MB"

    # 文件保存到 policies 目录
    policies_dir = locate_path("knowledge_base", base, "policies")
    os.makedirs(policies_dir, exist_ok=True)
    pieces_dir = locate_path("knowledge_base", base, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)

    policy_path = policy_file(base=base, filename=file.filename)
    pieces_path = piece_dir(base=base)
    with open(policy_path, "wb") as f:
        f.write(content)

    file_description = await split(policy_path, pieces_path)

    # 先看看同名文件是否已存在
    existing = (
        db.query(DBFile)
        .filter(DBFile.base == base,
                DBFile.file_name == file.filename)
        .first()
    )
    if existing:
        existing.file_size = file_size
        existing.file_description = file_description
        existing.uploaded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return {
            "base": existing.base,
            "file_name": existing.file_name,
            "file_description": existing.file_description,
            "file_path": existing.file_path,
            "uploaded_at": existing.uploaded_at,
            "file_size": existing.file_size,
            "message": "Existing file overwritten"
        }

    # 不存在则新建，显式传入 base，让 SQL 默认值生效也会回填
    new_file = DBFile(
        base=base,
        file_name=file.filename,
        file_description=file_description,
        file_path=policy_path,
        file_size=file_size
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return {
        "base": new_file.base,
        "file_name": new_file.file_name,
        "file_description": new_file.file_description,
        "file_path": new_file.file_path,
        "uploaded_at": new_file.uploaded_at,
        "file_size": new_file.file_size,
        "message": "File uploaded"
    }


@app.get("/api/v1/files/preview")
async def preview_file(
        file_name: str = Query(...),
        base: str = Query(...)
):
    file_path = policy_file(base=base, filename=unquote(file_name))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.delete("/api/v1/files")
async def delete_file(
        base: str = Query(...),
        file_name: str = Query(...),
        db: Session = Depends(get_db)
):
    # 查找数据库记录
    existing = (
        db.query(DBFile)
        .filter(DBFile.base == base, DBFile.file_name == file_name)
        .first()
    )

    if not existing:
        raise HTTPException(status_code=404, detail="File not found in database")

    # 构造文件路径
    policy_path = policy_file(base=base, filename=file_name)

    deleted_path = os.path.basename(policy_path)
    file_base, _ = os.path.splitext(deleted_path)
    output_format = "txt"
    pieces_path_1 = os.path.join(piece_dir(base=base), f"{file_base}_segmented.{output_format}")
    deleted_piece_path = policy_path.replace("policies", "pieces")
    pieces_path_2 = os.path.join(piece_dir(base=base), f"{deleted_piece_path}.{output_format}")

    # 删除 policy 文件
    if os.path.exists(policy_path):
        os.remove(policy_path)

    # 删除 pieces 文件
    if os.path.exists(pieces_path_1):
        os.remove(pieces_path_1)
    if os.path.exists(pieces_path_2):
        os.remove(pieces_path_2)
    # 删除数据库记录
    db.delete(existing)
    db.commit()

    return {
        "base": base,
        "file_name": file_name,
        "message": "File and related data deleted successfully"
    }


@app.post("/api/v1/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    question = db.query(DBQuestion).filter(
        DBQuestion.session_id == request.session_id,
        DBQuestion.question_id == request.question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问题不存在"
        )

    if question.rating is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该问题已经评分过"
        )

    question.rating = request.rating
    db.commit()

    return {
        "session_id": request.session_id,
        "question_id": request.question_id
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
