from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Grade(Base):
    __tablename__ = "grades"
    # Bir o'quvchi shu fandan, shu sanada, shu turda faqat bir marta baholanadi
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "date", "grade_type", name="uq_grade_once"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    score = Column(Integer, nullable=False)  # 2..5
    grade_type = Column(String(20), nullable=False, default="daily")  # daily | quiz | exam
    comment = Column(Text, nullable=True)

    subject = relationship("Subject", lazy="joined")

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names
