import datetime as dt
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.utils import today_local
from app.crud.academic import get_pupil_group_id
from app.models import Grade, GroupStudent, TeacherGroupSubject, User
from app.schemas.grade import GradeCreate


def create_grade(db: Session, teacher: User, data: GradeCreate) -> Grade:
    group_id = get_pupil_group_id(db, data.student_id)
    if group_id is None:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi yoki guruhga biriktirilmagan")
    teaches = db.query(TeacherGroupSubject).filter(
        TeacherGroupSubject.teacher_id == teacher.id,
        TeacherGroupSubject.group_id == group_id,
        TeacherGroupSubject.subject_id == data.subject_id).first()
    if not teaches:
        raise HTTPException(status_code=403, detail="Siz bu o'quvchiga bu fandan dars bermaysiz")
    if data.date > today_local():
        raise HTTPException(status_code=400, detail="Kelajak sanasiga baho qo'yib bo'lmaydi")

    ALREADY = "Bu o'quvchi shu sana va shu turda allaqachon baholangan. Bahoni o'zgartirib bo'lmaydi"
    if db.query(Grade.id).filter(Grade.student_id == data.student_id, Grade.subject_id == data.subject_id,
                                 Grade.date == data.date, Grade.grade_type == data.grade_type).first():
        raise HTTPException(status_code=409, detail=ALREADY)

    obj = Grade(**data.model_dump(), teacher_id=teacher.id)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=ALREADY)
    db.refresh(obj)
    return obj


def list_grades(db: Session, student_id: Optional[int] = None, teacher_id: Optional[int] = None,
                subject_id: Optional[int] = None, group_id: Optional[int] = None,
                date_from: Optional[dt.date] = None, date_to: Optional[dt.date] = None):
    q = db.query(Grade)
    if student_id is not None:
        q = q.filter(Grade.student_id == student_id)
    if teacher_id is not None:
        q = q.filter(Grade.teacher_id == teacher_id)
    if subject_id is not None:
        q = q.filter(Grade.subject_id == subject_id)
    if group_id is not None:
        q = q.join(GroupStudent, GroupStudent.student_id == Grade.student_id) \
             .filter(GroupStudent.group_id == group_id)
    if date_from:
        q = q.filter(Grade.date >= date_from)
    if date_to:
        q = q.filter(Grade.date <= date_to)
    return q.order_by(Grade.date.desc(), Grade.id.desc()).all()
