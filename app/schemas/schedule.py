import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import MAX_LESSON_MINUTES, MIN_LESSON_MINUTES


def _check_times(start: dt.time, end: dt.time) -> None:
    minutes = (dt.datetime.combine(dt.date.min, end) - dt.datetime.combine(dt.date.min, start)).total_seconds() / 60
    if minutes <= 0:
        raise ValueError("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak")
    if not (MIN_LESSON_MINUTES <= minutes <= MAX_LESSON_MINUTES):
        raise ValueError(
            f"Dars davomiyligi {MIN_LESSON_MINUTES}-{MAX_LESSON_MINUTES} daqiqa orasida bo'lishi kerak"
        )


class ScheduleBase(BaseModel):
    group_id: int
    subject_id: int
    day_of_week: int = Field(ge=1, le=7)  # 1=Dushanba ... 7=Yakshanba
    start_time: dt.time
    end_time: dt.time


class ScheduleCreate(ScheduleBase):
    """O'qituvchi yuborilmaydi: u guruh+fan bo'yicha tayinlangan o'qituvchidan olinadi."""

    @model_validator(mode="after")
    def check(self):
        _check_times(self.start_time, self.end_time)
        return self


class ScheduleUpdate(BaseModel):
    group_id: Optional[int] = None
    subject_id: Optional[int] = None
    day_of_week: Optional[int] = Field(default=None, ge=1, le=7)
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None

    @model_validator(mode="after")
    def check(self):
        if self.start_time and self.end_time:
            _check_times(self.start_time, self.end_time)
        return self


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    subject_id: int
    teacher_id: int
    day_of_week: int
    start_time: dt.time
    end_time: dt.time
    duration_minutes: int
    group_name: str
    subject_name: str
    subject_names: dict[str, str]
    teacher_name: str


class CurrentLessonResponse(BaseModel):
    current: Optional[ScheduleResponse] = None  # hozir ketayotgan dars
    next: Optional[ScheduleResponse] = None     # bugungi keyingi dars
