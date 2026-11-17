from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import relationship

from app.database import Base


class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)  # o'qituvchi biriktirgan fayl
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    group = relationship("Group", lazy="joined")
    subject = relationship("Subject", lazy="joined")
    file = relationship("StoredFile", lazy="joined")

    @property
    def group_name(self) -> str:
        return self.group.name

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"
    __table_args__ = (UniqueConstraint("homework_id", "student_id", name="uq_submission"),)

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    answer_text = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)

    homework = relationship("Homework")
    student = relationship("User", lazy="joined")
    file = relationship("StoredFile", lazy="joined")

    @property
    def student_name(self) -> str:
        return self.student.full_name
