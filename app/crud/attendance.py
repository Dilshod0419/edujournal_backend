import datetime as dt
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.utils import today_local
from app.crud.schedule import get_teacher_schedule
from app.models import Attendance, GroupStudent, User
from app.schemas.attendance import AttendanceBulkCreate


def get_attendance(db: Session, schedule_id: int, date: dt.date):
    return (db.query(Attendance)
            .filter(Attendance.schedule_id == schedule_id, Attendance.date == date)
            .order_by(Attendance.student_id).all())


def mark_attendance(db: Session, teacher: User, data: AttendanceBulkCreate):
    """Butun sinf davomatini bir so'rovda saqlaydi. Saqlangach o'zgartirib bo'lmaydi."""
    schedule = get_teacher_schedule(db, teacher, data.schedule_id)

    if data.date > today_local():
        raise HTTPException(status_code=400, detail="Kelajak sanasiga davomat qilib bo'lmaydi")
    if data.date.isoweekday() != schedule.day_of_week:
        raise HTTPException(status_code=400, detail="Bu sana dars jadvalidagi hafta kuniga mos kelmaydi")

    group_pupils = {r[0] for r in db.query(GroupStudent.student_id)
                    .filter(GroupStudent.group_id == schedule.group_id).all()}
    ids = [r.student_id for r in data.records]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=400, detail="Bir o'quvchi ikki marta kiritilgan")
    if not set(ids) <= group_pupils:
        raise HTTPException(status_code=400, detail="Ro'yxatda bu guruhga tegishli bo'lmagan o'quvchi bor")

    ALREADY = "Bu dars uchun davomat allaqachon saqlangan. Uni o'zgartirib bo'lmaydi"
    if get_attendance(db, schedule.id, data.date):
        raise HTTPException(status_code=409, detail=ALREADY)

    for rec in data.records:
        db.add(Attendance(schedule_id=schedule.id, student_id=rec.student_id,
                          date=data.date, status=rec.status))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=ALREADY)
    return get_attendance(db, schedule.id, data.date)


def get_student_attendance(db: Session, student_id: int, date_from: Optional[dt.date] = None,
                           date_to: Optional[dt.date] = None):
    q = db.query(Attendance).filter(Attendance.student_id == student_id)
    if date_from:
        q = q.filter(Attendance.date >= date_from)
    if date_to:
        q = q.filter(Attendance.date <= date_to)
    return q.order_by(Attendance.date.desc()).all()
