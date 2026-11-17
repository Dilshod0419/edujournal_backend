from datetime import date, datetime

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Time
from sqlalchemy.orm import relationship

from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="ck_schedule_day"),
        CheckConstraint("end_time > start_time", name="ck_schedule_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 1=Dushanba ... 7=Yakshanba
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    group = relationship("Group", lazy="joined")
    subject = relationship("Subject", lazy="joined")
    teacher = relationship("User", lazy="joined")

    @property
    def group_name(self) -> str:
        return self.group.name

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names

    @property
    def teacher_name(self) -> str:
        return self.teacher.full_name

    @property
    def duration_minutes(self) -> int:
        start = datetime.combine(date.min, self.start_time)
        end = datetime.combine(date.min, self.end_time)
        return int((end - start).total_seconds() // 60)
