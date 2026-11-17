import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import MAX_SCORE, MIN_SCORE

GradeType = Literal["daily", "quiz", "exam"]


class GradeCreate(BaseModel):
    """teacher_id yuborilmaydi: u tokendan olinadi."""
    student_id: int
    subject_id: int
    date: dt.date
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    grade_type: GradeType = "daily"
    comment: Optional[str] = None


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    teacher_id: int
    subject_id: int
    subject_name: str
    subject_names: dict[str, str]
    date: dt.date
    score: int
    grade_type: str
    comment: Optional[str] = None
