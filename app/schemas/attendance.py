import datetime as dt
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.enum import AttendanceStatus


class AttendanceItem(BaseModel):
    student_id: int
    status: AttendanceStatus = AttendanceStatus.present


class AttendanceBulkCreate(BaseModel):
    schedule_id: int
    date: dt.date
    records: List[AttendanceItem] = Field(min_length=1)


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    student_id: int
    student_name: str
    date: dt.date
    status: AttendanceStatus
