import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import MAX_SCORE, MIN_SCORE
from app.core.utils import ensure_aware
from app.schemas.file import FileInfo


# --- Uy vazifasi (teacher) ---
class HomeworkCreate(BaseModel):
    group_id: int
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: dt.datetime
    deadline: dt.datetime
    file_id: Optional[int] = None  # /files/upload orqali yuklangan fayl

    @model_validator(mode="after")
    def check_dates(self):
        if ensure_aware(self.deadline) <= ensure_aware(self.start_date):
            raise ValueError("Tugash muddati boshlanish vaqtidan keyin bo'lishi kerak")
        return self


class HomeworkUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[dt.datetime] = None
    deadline: Optional[dt.datetime] = None
    file_id: Optional[int] = None  # null yuborilsa fayl olib tashlanadi


class HomeworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    group_id: int
    subject_id: int
    group_name: str
    subject_name: str
    subject_names: dict[str, str]
    title: str
    description: Optional[str] = None
    start_date: dt.datetime
    deadline: dt.datetime
    file: Optional[FileInfo] = None
    created_at: Optional[dt.datetime] = None


# --- Vazifa javobi (pupil) ---
class SubmissionCreate(BaseModel):
    file_id: Optional[int] = None
    answer_text: Optional[str] = None

    @model_validator(mode="after")
    def not_empty(self):
        if not (self.file_id or (self.answer_text and self.answer_text.strip())):
            raise ValueError("Fayl yoki matnli javob kiritilishi kerak")
        return self


class SubmissionGrade(BaseModel):
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    feedback: Optional[str] = None


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    homework_id: int
    student_id: int
    student_name: str
    file: Optional[FileInfo] = None
    answer_text: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    submitted_at: dt.datetime
