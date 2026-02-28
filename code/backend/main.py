import io
import mimetypes
import os
import random
import json
import shutil
import uuid
from urllib.parse import unquote
from contextlib import asynccontextmanager

import uvicorn
import markdown as md_lib
import mammoth

import sys

# Environment Setup
try:
    from backend import env_setup
except ImportError:
    import env_setup

# try:
#     import lightrag
# except ImportError:
#     pass

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, HTMLResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime, timezone

from backend.model.doc_analysis import split, read_file
from backend.model.agent_router import route_stream, generate_follow_up_questions
from backend.model.rag_indexer import ingest_file
from sqlalchemy.orm import Session
from sqlalchemy import func
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

from backend.model.ques_assemble import generate_search_query
from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.root_path import (
    PIECES_DIR,
    KB_ROOT,
    locate_path,
    policy_file,
    course_file,
    piece_file,
    piece_dir,
    user_assignment_file,
    resolve_storage_path,
    uploads_dir,
    avatars_dir,
)

# Database & Models
from backend.database.connection import get_db, engine, SessionLocal, Base
from backend.database.models import DBSession, DBQuestion, DBMajor, DBCourse, DBFile, DBUser

# Schemas
from backend.schemas.chat import QuestionRequest, QuestionResponse, FeedbackRequest, FeedbackResponse
from backend.schemas.user import UserRegister, UserLogin, UserUpdate, PasswordUpdate


AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "1").strip().lower() not in {"0", "false", "no"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

# DEBUG: Print Database URL
from backend.database.connection import DATABASE_URL
print(f"\n[INFO] Backend starting with DATABASE_URL: {DATABASE_URL}\n")

# CORS配置
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/users/{user_id}")
async def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "account": user.account,
        "nickname": user.nickname,
        "role": user.role,
        "major_code": user.major_code,
        "avatar_path": user.avatar_path
    }

@app.put("/api/v1/users/{user_id}")
async def update_profile(user_id: int, update_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.nickname = update_data.nickname
    user.major_code = update_data.major_code
    db.commit()
    db.refresh(user)
    return {
        "message": "Profile updated",
        "user": {
            "user_id": user.user_id,
            "account": user.account,
            "nickname": user.nickname,
            "role": user.role,
            "major_code": user.major_code,
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

    # Create avatars directory (runtime data under .local_data)
    avatars_root = avatars_dir()
    os.makedirs(avatars_root, exist_ok=True)

    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"user_{user_id}_{int(datetime.now().timestamp())}{file_ext}"
    file_path = os.path.join(avatars_root, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Delete old avatar if exists
    if user.avatar_path:
        old_path = os.path.join(avatars_root, os.path.basename(user.avatar_path))
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
    avatars_root = avatars_dir()
    file_path = os.path.join(avatars_root, filename)
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
        role=user.role,
        major_code=user.major_code
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
            "role": db_user.role,
            "major_code": db_user.major_code,
            "avatar_path": db_user.avatar_path
        }
    }

@app.post("/api/v1/auth/admin_reset_password")
async def admin_reset_password(account: str = Query(...), new_password: str = Query(...), token: str = Query(...), db: Session = Depends(get_db)):
    expected = os.getenv("ADMIN_RESET_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = db.query(DBUser).filter(DBUser.account == account).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = pwd_context.hash(new_password)
    db.commit()
    return {"message": "Password reset", "user_id": user.user_id}

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


@app.post("/api/v1/chat/upload_temp")
async def upload_temp_file(file: UploadFile = File(...)):
    # Create temp directory
    temp_dir = uploads_dir("temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    # Generate unique ID
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(temp_dir, filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Preview content
    try:
        content = read_file(file_path)
        preview = content[:200] if content else ""
    except Exception as e:
        preview = "Error reading file"

    return {"temp_file_id": filename, "preview": preview}


@app.get("/api/v1/questions/stream")
async def stream_question(session_id: str, question_id: str, previous_questions: str, current_question: str, language: str = "en",
                          base: str = "lingnan", user_id: int = Query(None), temp_file_id: str = Query(None), db: Session = Depends(get_db)):

    temp_content = None
    if temp_file_id:
        temp_dir = uploads_dir("temp_uploads")
        # Security check: ensure temp_file_id is just a filename, not a path
        temp_file_id = os.path.basename(temp_file_id)
        file_path = os.path.join(temp_dir, temp_file_id)
        if os.path.exists(file_path):
            try:
                temp_content = read_file(file_path)
                print(f"DEBUG: Read temp file {temp_file_id}, length: {len(temp_content)}")
            except Exception as e:
                print(f"Error reading temp file: {e}")

    previous_questions_list = json.loads(previous_questions)

    # Determine user's accessible bases
    accessible_bases = ["public"]
    if user_id:
        user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
        if user:
            if user.role == 'student':
                if user.major_code:
                    courses = db.query(DBCourse).filter(DBCourse.major_code == user.major_code).all()
                    for c in courses:
                        accessible_bases.append(f"course_{c.course_code}")
                accessible_bases.append(f"user_{user_id}_private")
            elif user.role in ['teacher', 'admin']:
                courses = db.query(DBCourse).all()
                for c in courses:
                    accessible_bases.append(f"course_{c.course_code}")
                assignment_bases = db.query(DBFile.base).filter(DBFile.file_type == 'student_assignment').distinct().all()
                for b, in assignment_bases:
                    accessible_bases.append(b)
                knowledge_root = KB_ROOT
                if os.path.exists(knowledge_root):
                    for name in os.listdir(knowledge_root):
                        full_path = os.path.join(knowledge_root, name)
                        if os.path.isdir(full_path) and name.startswith("course_"):
                            accessible_bases.append(name)

    accessible_bases = list(set(accessible_bases))

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Auto-detect available model if not set or default
    # Priority: OLLAMA_GEN_MODEL env -> qwen3:8b -> qwen2.5:3b
    env_model = os.getenv("OLLAMA_GEN_MODEL")
    if not env_model:
        # Check available models
        try:
            import requests
            r = requests.get(f"{base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if "qwen3:8b" in models:
                    os.environ["OLLAMA_GEN_MODEL"] = "qwen3:8b"
                    print("DEBUG: Auto-detected and using qwen3:8b")
                elif "qwen2.5:3b" in models:
                    os.environ["OLLAMA_GEN_MODEL"] = "qwen2.5:3b"
        except:
            pass

    # --- Fetch conversation history from DB for context-aware query rewriting ---
    conversation_history = []
    try:
        recent_qas = db.query(DBQuestion).filter(
            DBQuestion.session_id == session_id
        ).order_by(DBQuestion.created_at.desc()).limit(3).all()
        for qa in reversed(recent_qas):  # oldest first
            conversation_history.append({
                "question": qa.current_question,
                "answer": (qa.answer or "")[:500]  # Truncate long answers
            })
        if conversation_history:
            print(f"DEBUG: Loaded {len(conversation_history)} previous Q&A turns for context")
    except Exception as e:
        print(f"Error fetching conversation history: {e}")

    gen_iter, references, rewritten_query, search_scope = await route_stream(
        current_question, previous_questions_list, language, accessible_bases,
        temp_file_content=temp_content, user_id=user_id,
        conversation_history=conversation_history
    )

    async def event_generator():
        print(f"DEBUG: Starting event_generator for session {session_id}")

        # Send reasoning data first
        if rewritten_query:
            yield f"data: {json.dumps({'rewritten_query': rewritten_query})}\n\n"
        if search_scope:
            yield f"data: {json.dumps({'search_scope': search_scope})}\n\n"

        full_answer = ""
        try:
            async for token in gen_iter:
                print(f"DEBUG: Received token: {token[:20]}..." if token else "DEBUG: Received empty token")
                if token:  # Ensure token is not empty
                    full_answer += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            print(f"Error during stream generation: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            # Don't return here, try to save partial answer if possible or just log

        print("DEBUG: Stream finished, sending references")
        # 发送引用文献消息，字段名为 references
        yield f"data: {json.dumps({'references': references})}\n\n"

        # Generate and send follow-up questions
        follow_up_questions = []
        try:
            if full_answer and len(full_answer) > 20:
                follow_up_questions = await generate_follow_up_questions(current_question, full_answer, language)
                if follow_up_questions:
                    yield f"data: {json.dumps({'follow_up_questions': follow_up_questions})}\n\n"
        except Exception as e:
            print(f"Error generating follow-up questions: {e}")

        # Save to DB
        print(f"DEBUG: Saving to DB. Session: {session_id}, User: {user_id}", flush=True)
        try:
            with SessionLocal() as db:
                # 1. Update/Create Session
                db_session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
                if not db_session:
                    # Check history limit (max 10) for this user
                    if user_id:
                        try:
                            current_count = db.query(DBSession).filter(DBSession.user_id == user_id).count()
                            if current_count >= 10:
                                # Delete oldest session(s)
                                num_to_delete = current_count - 9 # e.g., if 10, delete 1 to make room (result 9+1=10)
                                print(f"DEBUG: User {user_id} has {current_count} sessions. Deleting {num_to_delete} oldest.", flush=True)

                                oldest_sessions = db.query(DBSession).filter(DBSession.user_id == user_id)\
                                    .order_by(DBSession.last_activity.asc())\
                                    .limit(num_to_delete).all()

                                for old_sess in oldest_sessions:
                                    # Manually delete related questions first (if cascade not set)
                                    db.query(DBQuestion).filter(DBQuestion.session_id == old_sess.session_id).delete()
                                    db.delete(old_sess)
                                    print(f"DEBUG: Deleted old session {old_sess.session_id}", flush=True)
                        except Exception as e:
                            print(f"Error enforcing history limit: {e}", flush=True)

                    # New session, use current question as title
                    title = current_question[:50] + "..." if len(current_question) > 50 else current_question
                    db_session = DBSession(session_id=session_id, user_id=user_id, title=title)
                    db.add(db_session)
                    print(f"DEBUG: Created new session {session_id} for user {user_id}", flush=True)
                else:
                    # Update last activity
                    db_session.last_activity = func.now()
                    # If user_id was missing (guest started, then logged in? unlikely flow but safe to set)
                    if user_id and not db_session.user_id:
                        db_session.user_id = user_id
                        print(f"DEBUG: Associated session {session_id} with user {user_id}", flush=True)

                # Commit session changes FIRST to satisfy Foreign Key constraints
                db.commit()

                # 2. Save Question
                db_question = DBQuestion(
                    session_id=session_id,
                    question_id=question_id,
                    previous_questions=json.loads(previous_questions), # Store as JSON
                    current_question=current_question,
                    answer=full_answer,
                    references=references,
                    rewritten_question=rewritten_query,
                    search_scope=search_scope,
                    follow_up_questions=follow_up_questions,
                    rating=None
                )
                db.add(db_question)
                db.commit()
                print(f"DEBUG: DB save successful. Question saved with ID: {db_question.question_id}", flush=True)
        except Exception as e:
            print(f"Error saving to DB: {e}", flush=True)
            import traceback
            traceback.print_exc()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/public/policies")
async def list_policies(db: Session = Depends(get_db)):
    files = db.query(DBFile).filter(DBFile.file_type == 'policy').all()
    return {"files": files}

@app.get("/api/v1/majors")
async def list_majors(db: Session = Depends(get_db)):
    majors = db.query(DBMajor).all()
    return {"majors": majors}

@app.get("/api/v1/courses")
async def list_courses(user_id: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(DBCourse)
    if user_id:
        user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
        if user and user.role == 'student' and user.major_code:
            query = query.filter(DBCourse.major_code == user.major_code)

    courses = query.all()
    return {"courses": courses}

@app.get("/api/v1/courses/{code}/files")
async def list_course_files(code: str, db: Session = Depends(get_db)):
    files = db.query(DBFile).filter(
        DBFile.related_course_code == code,
        DBFile.file_type.in_(['course_ppt', 'course_rubric', 'course_material'])
    ).all()
    return {"files": files}

@app.post("/api/v1/courses/{code}/files")
async def upload_course_file(
    code: str,
    user_id: int = Form(...),
    file_type: str = Form(...), # course_ppt, course_rubric
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user or (user.role != 'teacher' and user.role != 'admin'):
        raise HTTPException(status_code=403, detail="Only teachers or admins can upload course files")

    # Logic to save file and ingest (similar to previous upload)
    # For now, just save DB record to demonstrate structure
    # In real impl, would call ingest_file with specific scope

    content = await file.read()
    size_kb = len(content) / 1024
    file_size = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.1f}MB"

    # Define path
    # 修正：将路径保存到 course_{code}/files 下，而不是 courses/{code}
    # 保持与 base 命名一致：base="course_{code}"
    # save_dir = locate_path("courses", code)
    save_dir = locate_path(f"course_{code}", "files")
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(content)

    db_file = DBFile(
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        access_level='internal',
        base=f"course_{code}",
        related_course_code=code,
        uploader_id=user_id
    )
    db.add(db_file)
    db.commit()

    # Trigger ingestion (Async)
    try:
        # ingest_file expects absolute path or resolvable path
        await ingest_file(f"course_{code}", file_path)
    except Exception as e:
        print(f"Error indexing file: {e}")

    return {"message": "File uploaded"}

@app.post("/api/v1/admin/policies")
async def upload_policy(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user or user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can upload policies")

    content = await file.read()
    size_kb = len(content) / 1024
    file_size = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.1f}MB"

    save_dir = locate_path("public", "policies")
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(content)

    db_file = DBFile(
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type='policy',
        access_level='public',
        base="public",
        uploader_id=user_id
    )
    db.add(db_file)
    db.commit()

    # Trigger ingestion (Async)
    try:
        await ingest_file("public", file_path)
    except Exception as e:
        print(f"Error indexing policy: {e}")

    return {"message": "Policy uploaded"}

@app.post("/api/v1/my/assignments")
async def upload_assignment(
    course_code: str = Form(...),
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user or user.role != 'student':
        raise HTTPException(status_code=403, detail="Only students can upload assignments")

    content = await file.read()
    size_kb = len(content) / 1024
    file_size = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.1f}MB"

    save_dir = locate_path("users", str(user_id), "assignments")
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(content)

    db_file = DBFile(
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type='student_assignment',
        access_level='private',
        base=f"user_{user_id}_private",
        related_course_code=course_code,
        uploader_id=user_id
    )
    db.add(db_file)
    db.commit()

    # Trigger ingestion (Async)
    try:
        await ingest_file(f"user_{user_id}_private", file_path)
    except Exception as e:
        print(f"Error indexing assignment: {e}")

    return {"message": "Assignment uploaded"}

@app.delete("/api/v1/files/{file_id}")
async def delete_file_by_id(
    file_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    file = db.query(DBFile).filter(DBFile.file_id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=403, detail="User not found")

    # Permission Logic
    can_delete = False
    if user.role == 'admin':
        can_delete = True
    elif user.role == 'teacher':
        # Teachers can delete course files (assuming they manage the course)
        # For simplicity, allowing teachers to delete any course file for now,
        # or strictly their own uploads. Let's go with their own uploads or course files.
        if file.file_type in ['course_ppt', 'course_rubric', 'course_material']:
             can_delete = True
    elif user.role == 'student':
        # Students can only delete their own assignments
        if file.uploader_id == user.user_id and file.file_type == 'student_assignment':
            can_delete = True

    if not can_delete:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Delete from disk (stored path may be legacy)
    resolved_path = resolve_storage_path(file.file_path)
    if resolved_path and os.path.exists(resolved_path):
        os.remove(resolved_path)

    # Delete pieces (traditional ingestion output)
    try:
        pieces_path = os.path.join(piece_dir(base=file.base), f"{file.file_name}.txt")
        if os.path.exists(pieces_path):
            os.remove(pieces_path)
    except Exception as e:
        print(f"Warning: failed to delete pieces for file_id={file.file_id}: {e}")

    # Delete vectors (pgvector)
    try:
        from backend.model.vector_store import delete_documents_for_file

        deleted_vectors = delete_documents_for_file(collection_name=file.base, original_file=file.file_name)
        if deleted_vectors:
            print(f"DEBUG: Deleted {deleted_vectors} vectors for file_id={file.file_id}")
    except Exception as e:
        print(f"Warning: failed to delete vectors for file_id={file.file_id}: {e}")

    db.delete(file)
    db.commit()

    return {"message": "File deleted"}


@app.get("/api/v1/files/preview")
async def preview_file(
        file_name: str = Query(...),
        base: str = Query(...)
):
    decoded_name = unquote(file_name)
    file_path = None

    if base == "public":
        file_path = policy_file(base=base, filename=decoded_name)
    elif base.startswith("course_"):
        file_path = course_file(base=base, filename=decoded_name)
    elif base.startswith("user_") and base.endswith("_private"):
        parts = base.split("_")
        if len(parts) >= 3:
            try:
                user_id = int(parts[1])
                file_path = user_assignment_file(user_id=user_id, filename=decoded_name)
            except ValueError:
                pass

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.delete("/api/v1/files")
async def delete_file_legacy(
        base: str = Query(...),
        file_name: str = Query(...),
        user_id: int = Query(...),
        db: Session = Depends(get_db)
):
    """Legacy delete endpoint.

    Keeps compatibility for callers that only know (base, file_name),
    but routes through the authoritative delete-by-id flow.
    """
    existing = (
        db.query(DBFile)
        .filter(DBFile.base == base, DBFile.file_name == file_name)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="File not found in database")

    return await delete_file_by_id(file_id=existing.file_id, user_id=user_id, db=db)


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


@app.get("/api/v1/users/{user_id}/sessions")
async def get_user_sessions(user_id: int, limit: int = 10, db: Session = Depends(get_db)):
    sessions = db.query(DBSession).filter(DBSession.user_id == user_id)\
        .order_by(DBSession.last_activity.desc())\
        .limit(limit)\
        .all()

    return [
        {
            "session_id": s.session_id,
            "title": s.title or "New Chat",
            "created_at": s.created_at,
            "last_activity": s.last_activity
        }
        for s in sessions
    ]

@app.get("/api/v1/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    questions = db.query(DBQuestion).filter(DBQuestion.session_id == session_id)\
        .order_by(DBQuestion.created_at.asc())\
        .all()

    messages = []
    for q in questions:
        # Add User Question
        messages.append({
            "role": "user",
            "content": q.current_question,
            "id": q.question_id + "_u"
        })
        # Add Assistant Answer
        messages.append({
            "role": "assistant",
            "content": q.answer,
            "references": q.references,
            "id": q.question_id + "_a",
            "rating": q.rating
        })

    return messages


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str, user_id: int = Query(...), db: Session = Depends(get_db)):
    # Verify session exists and belongs to user
    session = db.query(DBSession).filter(
        DBSession.session_id == session_id,
        DBSession.user_id == user_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    try:
        # Delete related questions first
        db.query(DBQuestion).filter(DBQuestion.session_id == session_id).delete()

        # Delete session
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

    return {"message": "Session deleted successfully"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
