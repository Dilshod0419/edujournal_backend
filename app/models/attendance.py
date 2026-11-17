from sqlalchemy import Column, Date, Enum as SQLEnum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enum import AttendanceStatus


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("schedule_id", "student_id", "date", name="uq_attendance"),
    )

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(
        SQLEnum(AttendanceStatus, name="attendancestatus"),
        nullable=False,
        default=AttendanceStatus.present,
    )

    student = relationship("User", lazy="joined")

    @property
    def student_name(self) -> str:
        return self.student.full_name
