from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # o'zbekcha (asosiy)
    name_ru = Column(String(100), nullable=True)
    name_en = Column(String(100), nullable=True)

    @property
    def names(self) -> dict:
        return {"uz": self.name, "ru": self.name_ru or self.name, "en": self.name_en or self.name}


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=expression.true())

    students = relationship("GroupStudent", back_populates="group")


class GroupStudent(Base):
    """O'quvchi faqat bitta guruhda (sinfda) bo'ladi."""
    __tablename__ = "group_students"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    group = relationship("Group", back_populates="students")
    student = relationship("User")


class GroupSubject(Base):
    """Fan guruhga (sinfga) biriktirilgan."""
    __tablename__ = "group_subjects"
    __table_args__ = (UniqueConstraint("group_id", "subject_id", name="uq_group_subject"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    group = relationship("Group", lazy="joined")
    subject = relationship("Subject", lazy="joined")

    @property
    def group_name(self) -> str:
        return self.group.name

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names


class TeacherSubject(Base):
    """O'qituvchi qaysi fanlarni o'ta oladi."""
    __tablename__ = "teacher_subjects"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id", name="uq_teacher_subject"),)

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    subject = relationship("Subject", lazy="joined")

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names


class TeacherGroupSubject(Base):
    """Aynan shu guruhda shu fanni qaysi o'qituvchi o'tadi (bitta guruh+fan = bitta o'qituvchi)."""
    __tablename__ = "teacher_group_subjects"
    __table_args__ = (UniqueConstraint("group_id", "subject_id", name="uq_tgs_group_subject"),)

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    teacher = relationship("User", lazy="joined")
    group = relationship("Group", lazy="joined")
    subject = relationship("Subject", lazy="joined")

    @property
    def teacher_name(self) -> str:
        return self.teacher.full_name

    @property
    def group_name(self) -> str:
        return self.group.name

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names
