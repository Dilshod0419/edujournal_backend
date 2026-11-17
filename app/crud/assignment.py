from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.utils import ensure_aware, now_local
from app.crud import file as crud_file
from app.crud.academic import get_pupil_group_id
from app.models import Homework, HomeworkSubmission, TeacherGroupSubject, User
from app.schemas.assignment import HomeworkCreate, HomeworkUpdate, SubmissionCreate, SubmissionGrade


# ==================== O'QITUVCHI ====================

def create_homework(db: Session, teacher: User, data: HomeworkCreate) -> Homework:
    teaches = db.query(TeacherGroupSubject).filter(
        TeacherGroupSubject.teacher_id == teacher.id,
        TeacherGroupSubject.group_id == data.group_id,
        TeacherGroupSubject.subject_id == data.subject_id).first()
    if not teaches:
        raise HTTPException(status_code=403, detail="Siz bu guruhda bu fandan dars bermaysiz")
    crud_file.require_own_file(db, teacher, data.file_id)
    obj = Homework(teacher_id=teacher.id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_own_homework(db: Session, teacher: User, homework_id: int) -> Homework:
    obj = db.get(Homework, homework_id)
    if obj is None or obj.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Uy vazifasi topilmadi")
    return obj


def list_teacher_homeworks(db: Session, teacher: User, group_id: Optional[int] = None,
                           subject_id: Optional[int] = None, skip: int = 0, limit: int = 100):
    q = db.query(Homework).filter(Homework.teacher_id == teacher.id)
    if group_id is not None:
        q = q.filter(Homework.group_id == group_id)
    if subject_id is not None:
        q = q.filter(Homework.subject_id == subject_id)
    return q.order_by(Homework.deadline.desc()).offset(skip).limit(limit).all()


def update_homework(db: Session, teacher: User, homework_id: int, data: HomeworkUpdate) -> Homework:
    obj = get_own_homework(db, teacher, homework_id)
    old_file_id = obj.file_id
    values = data.model_dump(exclude_unset=True)
    if "file_id" in values:
        crud_file.require_own_file(db, teacher, values["file_id"])
        obj.file_id = values.pop("file_id")  # None bo'lsa fayl olib tashlanadi
    for key, value in values.items():
        if value is not None:
            setattr(obj, key, value)
    if ensure_aware(obj.deadline) <= ensure_aware(obj.start_date):
        db.rollback()
        raise HTTPException(status_code=400, detail="Tugash muddati boshlanish vaqtidan keyin bo'lishi kerak")
    db.commit()
    if old_file_id != obj.file_id:
        crud_file.delete_if_orphan(db, old_file_id)
    db.refresh(obj)
    return obj


def delete_homework(db: Session, teacher: User, homework_id: int) -> None:
    obj = get_own_homework(db, teacher, homework_id)
    if db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework_id).first():
        raise HTTPException(status_code=409,
                            detail="Vazifaga javoblar yuklangan, o'chirib bo'lmaydi")
    file_id = obj.file_id
    db.delete(obj)
    db.commit()
    crud_file.delete_if_orphan(db, file_id)


def list_submissions(db: Session, teacher: User, homework_id: int):
    get_own_homework(db, teacher, homework_id)
    return (db.query(HomeworkSubmission)
            .filter(HomeworkSubmission.homework_id == homework_id)
            .order_by(HomeworkSubmission.submitted_at).all())


def grade_submission(db: Session, teacher: User, submission_id: int,
                     data: SubmissionGrade) -> HomeworkSubmission:
    sub = db.get(HomeworkSubmission, submission_id)
    if sub is None or sub.homework.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Javob topilmadi")
    if sub.score is not None:
        raise HTTPException(status_code=409, detail="Bu ish allaqachon baholangan. Bahoni o'zgartirib bo'lmaydi")
    sub.score = data.score
    sub.feedback = data.feedback
    db.commit()
    db.refresh(sub)
    return sub


# ==================== O'QUVCHI ====================

def list_pupil_homeworks(db: Session, pupil: User, subject_id: Optional[int] = None):
    group_id = get_pupil_group_id(db, pupil.id)
    if group_id is None:
        return []
    q = db.query(Homework).filter(Homework.group_id == group_id)
    if subject_id is not None:
        q = q.filter(Homework.subject_id == subject_id)
    return q.order_by(Homework.deadline.desc()).all()


def submit_homework(db: Session, pupil: User, homework_id: int,
                    data: SubmissionCreate) -> HomeworkSubmission:
    """O'quvchi id si tokendan olinadi. Muddat tugamaguncha qayta yuklash mumkin."""
    hw = db.get(Homework, homework_id)
    if hw is None or hw.group_id != get_pupil_group_id(db, pupil.id):
        raise HTTPException(status_code=404, detail="Uy vazifasi topilmadi")

    now = now_local()
    if now < ensure_aware(hw.start_date):
        raise HTTPException(status_code=400, detail="Vazifa topshirish hali boshlanmagan")
    if now > ensure_aware(hw.deadline):
        raise HTTPException(status_code=400, detail="Vazifa topshirish muddati tugagan")

    crud_file.require_own_file(db, pupil, data.file_id)
    sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework_id,
                                              HomeworkSubmission.student_id == pupil.id).first()
    old_file_id = sub.file_id if sub else None
    if sub is None:
        sub = HomeworkSubmission(homework_id=homework_id, student_id=pupil.id)
        db.add(sub)
    elif sub.score is not None:
        raise HTTPException(status_code=400, detail="Baholangan vazifani o'zgartirib bo'lmaydi")

    sub.file_id = data.file_id
    sub.answer_text = data.answer_text
    sub.submitted_at = now
    db.commit()
    if old_file_id != sub.file_id:
        crud_file.delete_if_orphan(db, old_file_id)
    db.refresh(sub)
    return sub


def list_pupil_submissions(db: Session, pupil: User):
    return (db.query(HomeworkSubmission)
            .filter(HomeworkSubmission.student_id == pupil.id)
            .order_by(HomeworkSubmission.submitted_at.desc()).all())
