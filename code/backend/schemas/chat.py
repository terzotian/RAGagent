from pydantic import BaseModel, Field
from typing import List, Dict, Optional

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
