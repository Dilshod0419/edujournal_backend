import datetime as dt
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import MAX_LESSON_MINUTES, MIN_LESSON_MINUTES
from app.core.utils import now_local
from app.models import Group, GroupSubject, Schedule, Subject, TeacherGroupSubject, User
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


def _minutes(start: dt.time, end: dt.time) -> float:
    return (dt.datetime.combine(dt.date.min, end) - dt.datetime.combine(dt.date.min, start)).total_seconds() / 60


def _validate(db: Session, group_id: int, subject_id: int, day: int, start: dt.time,
              end: dt.time, exclude_id: Optional[int] = None) -> int:
    """Tekshiradi va dars o'qituvchisining id sini qaytaradi."""
    minutes = _minutes(start, end)
    if minutes <= 0:
        raise HTTPException(status_code=400, detail="Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak")
    if not (MIN_LESSON_MINUTES <= minutes <= MAX_LESSON_MINUTES):
        raise HTTPException(
            status_code=400,
            detail=f"Dars davomiyligi {MIN_LESSON_MINUTES}-{MAX_LESSON_MINUTES} daqiqa orasida bo'lishi kerak")

    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    if not group.is_active:
        raise HTTPException(status_code=400, detail="Guruh faol emas")
    if db.get(Subject, subject_id) is None:
        raise HTTPException(status_code=404, detail="Fan topilmadi")
    if not db.query(GroupSubject).filter(GroupSubject.group_id == group_id,
                                         GroupSubject.subject_id == subject_id).first():
        raise HTTPException(status_code=400, detail="Bu fan guruhga biriktirilmagan")

    tgs = db.query(TeacherGroupSubject).filter(TeacherGroupSubject.group_id == group_id,
                                               TeacherGroupSubject.subject_id == subject_id).first()
    if tgs is None:
        raise HTTPException(status_code=400, detail="Bu fan uchun guruhga o'qituvchi tayinlanmagan")
    if not tgs.teacher.is_active:
        raise HTTPException(status_code=400, detail="Tayinlangan o'qituvchi faol emas")

    overlap = db.query(Schedule).filter(Schedule.day_of_week == day,
                                        Schedule.start_time < end, Schedule.end_time > start)
    if exclude_id is not None:
        overlap = overlap.filter(Schedule.id != exclude_id)
    if overlap.filter(Schedule.group_id == group_id).first():
        raise HTTPException(status_code=409, detail="Guruhning bu vaqtda boshqa darsi bor")
    if overlap.filter(Schedule.teacher_id == tgs.teacher_id).first():
        raise HTTPException(status_code=409, detail="O'qituvchining bu vaqtda boshqa darsi bor")
    return tgs.teacher_id


def create_schedule(db: Session, data: ScheduleCreate) -> Schedule:
    teacher_id = _validate(db, data.group_id, data.subject_id, data.day_of_week,
                           data.start_time, data.end_time)
    obj = Schedule(**data.model_dump(), teacher_id=teacher_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_schedule(db: Session, schedule_id: int) -> Optional[Schedule]:
    return db.get(Schedule, schedule_id)


def get_schedules(db: Session, skip: int = 0, limit: int = 200, group_id: Optional[int] = None,
                  teacher_id: Optional[int] = None, day_of_week: Optional[int] = None):
    q = db.query(Schedule)
    if group_id is not None:
        q = q.filter(Schedule.group_id == group_id)
    if teacher_id is not None:
        q = q.filter(Schedule.teacher_id == teacher_id)
    if day_of_week is not None:
        q = q.filter(Schedule.day_of_week == day_of_week)
    return q.order_by(Schedule.day_of_week, Schedule.start_time).offset(skip).limit(limit).all()


def update_schedule(db: Session, schedule_id: int, data: ScheduleUpdate) -> Schedule:
    obj = get_schedule(db, schedule_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Jadval topilmadi")
    values = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    merged = {
        "group_id": obj.group_id, "subject_id": obj.subject_id, "day_of_week": obj.day_of_week,
        "start_time": obj.start_time, "end_time": obj.end_time, **values,
    }
    teacher_id = _validate(db, merged["group_id"], merged["subject_id"], merged["day_of_week"],
                           merged["start_time"], merged["end_time"], exclude_id=schedule_id)
    for key, value in merged.items():
        setattr(obj, key, value)
    obj.teacher_id = teacher_id
    db.commit()
    db.refresh(obj)
    return obj


def delete_schedule(db: Session, schedule_id: int) -> None:
    obj = get_schedule(db, schedule_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Jadval topilmadi")
    db.delete(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu darsga davomat yozilgan, o'chirib bo'lmaydi")


def get_teacher_schedule(db: Session, teacher: User, schedule_id: int) -> Schedule:
    obj = get_schedule(db, schedule_id)
    if obj is None or obj.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
    return obj


def get_current_lesson(db: Session, teacher_id: int) -> dict:
    """Hozirgi (Toshkent) vaqt va hafta kuniga qarab o'qituvchining joriy va keyingi darsi."""
    now = now_local()
    t = now.time()  # vaqt zonasiz
    today = (db.query(Schedule)
             .filter(Schedule.teacher_id == teacher_id, Schedule.day_of_week == now.isoweekday())
             .order_by(Schedule.start_time).all())
    current = next((s for s in today if s.start_time <= t < s.end_time), None)
    upcoming = next((s for s in today if s.start_time > t), None)
    return {"current": current, "next": upcoming}
