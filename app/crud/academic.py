from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (Group, GroupStudent, GroupSubject, RoleEnum, Schedule, Subject,
                        TeacherGroupSubject, TeacherSubject, User)
from app.schemas.academic import GroupCreate, GroupUpdate, SubjectCreate, SubjectUpdate, TeacherAssign


# ---------- yordamchi ----------

def _get_or_404(db: Session, model, obj_id: int, message: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=message)
    return obj


def _commit(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict_message)


def get_pupil_group_id(db: Session, pupil_id: int) -> Optional[int]:
    gs = db.query(GroupStudent).filter(GroupStudent.student_id == pupil_id).first()
    return gs.group_id if gs else None


def get_group_subject_ids(db: Session, group_id: int) -> list[int]:
    rows = db.query(GroupSubject.subject_id).filter(GroupSubject.group_id == group_id).all()
    return [r[0] for r in rows]


# ---------- FANLAR ----------

def create_subject(db: Session, data: SubjectCreate) -> Subject:
    if db.query(Subject).filter(func.lower(Subject.name) == data.name.lower()).first():
        raise HTTPException(status_code=409, detail="Bunday fan allaqachon mavjud")
    obj = Subject(name=data.name, name_ru=data.name_ru, name_en=data.name_en)
    db.add(obj)
    _commit(db, "Bunday fan allaqachon mavjud")
    db.refresh(obj)
    return obj


def get_subjects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Subject).order_by(Subject.name).offset(skip).limit(limit).all()


def update_subject(db: Session, subject_id: int, data: SubjectUpdate) -> Subject:
    obj = _get_or_404(db, Subject, subject_id, "Fan topilmadi")
    dup = db.query(Subject).filter(func.lower(Subject.name) == data.name.lower(),
                                   Subject.id != subject_id).first()
    if dup:
        raise HTTPException(status_code=409, detail="Bunday fan allaqachon mavjud")
    obj.name = data.name
    obj.name_ru = data.name_ru
    obj.name_en = data.name_en
    db.commit()
    db.refresh(obj)
    return obj


def delete_subject(db: Session, subject_id: int) -> None:
    obj = _get_or_404(db, Subject, subject_id, "Fan topilmadi")
    msg = "Fan guruh, o'qituvchi yoki boshqa ma'lumotlarga bog'langan, o'chirib bo'lmaydi"
    if (db.query(GroupSubject).filter(GroupSubject.subject_id == subject_id).first()
            or db.query(TeacherSubject).filter(TeacherSubject.subject_id == subject_id).first()):
        raise HTTPException(status_code=409, detail=msg)
    db.delete(obj)
    _commit(db, msg)


# ---------- GURUHLAR ----------

def create_group(db: Session, data: GroupCreate) -> Group:
    if db.query(Group).filter(func.lower(Group.name) == data.name.lower()).first():
        raise HTTPException(status_code=409, detail="Bunday guruh allaqachon mavjud")
    obj = Group(name=data.name)
    db.add(obj)
    _commit(db, "Bunday guruh allaqachon mavjud")
    db.refresh(obj)
    return obj


def get_groups(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None):
    q = db.query(Group)
    if is_active is not None:
        q = q.filter(Group.is_active == is_active)
    return q.order_by(Group.name).offset(skip).limit(limit).all()


def update_group(db: Session, group_id: int, data: GroupUpdate) -> Group:
    obj = _get_or_404(db, Group, group_id, "Guruh topilmadi")
    values = data.model_dump(exclude_unset=True)
    if values.get("name"):
        dup = db.query(Group).filter(func.lower(Group.name) == values["name"].lower(),
                                     Group.id != group_id).first()
        if dup:
            raise HTTPException(status_code=409, detail="Bunday guruh allaqachon mavjud")
    for key, value in values.items():
        if value is not None:
            setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_group(db: Session, group_id: int) -> None:
    obj = _get_or_404(db, Group, group_id, "Guruh topilmadi")
    db.delete(obj)
    _commit(db, "Guruhga o'quvchi, fan yoki dars jadvali bog'langan. O'chirish o'rniga faolsizlantiring")


# ---------- GURUH <-> O'QUVCHI ----------

def get_group_pupils(db: Session, group_id: int):
    _get_or_404(db, Group, group_id, "Guruh topilmadi")
    return (db.query(User)
            .join(GroupStudent, GroupStudent.student_id == User.id)
            .filter(GroupStudent.group_id == group_id)
            .order_by(User.last_name, User.first_name)
            .all())


def add_pupil_to_group(db: Session, group_id: int, pupil_id: int) -> None:
    group = _get_or_404(db, Group, group_id, "Guruh topilmadi")
    if not group.is_active:
        raise HTTPException(status_code=400, detail="Guruh faol emas")
    pupil = db.get(User, pupil_id)
    if pupil is None or pupil.role != RoleEnum.pupil:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    link = db.query(GroupStudent).filter(GroupStudent.student_id == pupil_id).first()
    if link:
        link.group_id = group_id  # o'quvchi boshqa sinfga ko'chiriladi
    else:
        db.add(GroupStudent(group_id=group_id, student_id=pupil_id))
    _commit(db, "O'quvchini guruhga qo'shib bo'lmadi")


def remove_pupil_from_group(db: Session, group_id: int, pupil_id: int) -> None:
    link = db.query(GroupStudent).filter(GroupStudent.group_id == group_id,
                                         GroupStudent.student_id == pupil_id).first()
    if link is None:
        raise HTTPException(status_code=404, detail="O'quvchi bu guruhda emas")
    db.delete(link)
    db.commit()


# ---------- GURUH <-> FAN ----------

def list_group_subjects(db: Session, group_id: int):
    _get_or_404(db, Group, group_id, "Guruh topilmadi")
    return db.query(GroupSubject).filter(GroupSubject.group_id == group_id).all()


def add_subject_to_group(db: Session, group_id: int, subject_id: int) -> GroupSubject:
    _get_or_404(db, Group, group_id, "Guruh topilmadi")
    _get_or_404(db, Subject, subject_id, "Fan topilmadi")
    if db.query(GroupSubject).filter(GroupSubject.group_id == group_id,
                                     GroupSubject.subject_id == subject_id).first():
        raise HTTPException(status_code=409, detail="Fan bu guruhga allaqachon biriktirilgan")
    obj = GroupSubject(group_id=group_id, subject_id=subject_id)
    db.add(obj)
    _commit(db, "Fan bu guruhga allaqachon biriktirilgan")
    db.refresh(obj)
    return obj


def remove_subject_from_group(db: Session, group_id: int, subject_id: int) -> None:
    obj = db.query(GroupSubject).filter(GroupSubject.group_id == group_id,
                                        GroupSubject.subject_id == subject_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Bunday biriktirish topilmadi")
    if (db.query(TeacherGroupSubject).filter(TeacherGroupSubject.group_id == group_id,
                                             TeacherGroupSubject.subject_id == subject_id).first()
            or db.query(Schedule).filter(Schedule.group_id == group_id,
                                         Schedule.subject_id == subject_id).first()):
        raise HTTPException(status_code=409,
                            detail="Avval bu fan bo'yicha o'qituvchi tayinlashni va dars jadvalini o'chiring")
    db.delete(obj)
    db.commit()


# ---------- O'QITUVCHI <-> FAN (qaysi fanlarni o'ta oladi) ----------

def _get_teacher(db: Session, teacher_id: int) -> User:
    teacher = db.get(User, teacher_id)
    if teacher is None or teacher.role != RoleEnum.teacher:
        raise HTTPException(status_code=404, detail="O'qituvchi topilmadi")
    return teacher


def list_teacher_subjects(db: Session, teacher_id: int):
    _get_teacher(db, teacher_id)
    return db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id).all()


def add_subject_to_teacher(db: Session, teacher_id: int, subject_id: int) -> TeacherSubject:
    _get_teacher(db, teacher_id)
    _get_or_404(db, Subject, subject_id, "Fan topilmadi")
    if db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id,
                                       TeacherSubject.subject_id == subject_id).first():
        raise HTTPException(status_code=409, detail="Fan bu o'qituvchiga allaqachon biriktirilgan")
    obj = TeacherSubject(teacher_id=teacher_id, subject_id=subject_id)
    db.add(obj)
    _commit(db, "Fan bu o'qituvchiga allaqachon biriktirilgan")
    db.refresh(obj)
    return obj


def remove_subject_from_teacher(db: Session, teacher_id: int, subject_id: int) -> None:
    obj = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id,
                                          TeacherSubject.subject_id == subject_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Bunday biriktirish topilmadi")
    if db.query(TeacherGroupSubject).filter(TeacherGroupSubject.teacher_id == teacher_id,
                                            TeacherGroupSubject.subject_id == subject_id).first():
        raise HTTPException(status_code=409,
                            detail="O'qituvchi bu fanni guruhlarda o'tmoqda. Avval tayinlashni o'chiring")
    db.delete(obj)
    db.commit()


# ---------- O'QITUVCHI <-> GURUH + FAN ----------

def list_teacher_assignments(db: Session, teacher_id: Optional[int] = None,
                             group_id: Optional[int] = None):
    q = db.query(TeacherGroupSubject)
    if teacher_id is not None:
        q = q.filter(TeacherGroupSubject.teacher_id == teacher_id)
    if group_id is not None:
        q = q.filter(TeacherGroupSubject.group_id == group_id)
    return q.order_by(TeacherGroupSubject.id).all()


def assign_teacher(db: Session, data: TeacherAssign) -> TeacherGroupSubject:
    teacher = _get_teacher(db, data.teacher_id)
    if not teacher.is_active:
        raise HTTPException(status_code=400, detail="O'qituvchi faol emas")
    if not db.query(GroupSubject).filter(GroupSubject.group_id == data.group_id,
                                         GroupSubject.subject_id == data.subject_id).first():
        raise HTTPException(status_code=400, detail="Bu fan avval guruhga biriktirilishi kerak")
    if not db.query(TeacherSubject).filter(TeacherSubject.teacher_id == data.teacher_id,
                                           TeacherSubject.subject_id == data.subject_id).first():
        raise HTTPException(status_code=400, detail="Bu fan avval o'qituvchiga biriktirilishi kerak")

    obj = db.query(TeacherGroupSubject).filter(
        TeacherGroupSubject.group_id == data.group_id,
        TeacherGroupSubject.subject_id == data.subject_id).first()

    if obj is None:
        obj = TeacherGroupSubject(teacher_id=data.teacher_id, group_id=data.group_id,
                                  subject_id=data.subject_id)
        db.add(obj)
    elif obj.teacher_id != data.teacher_id:
        # O'qituvchi almashtirilmoqda: mavjud dars jadvallari ham yangi o'qituvchiga o'tadi
        schedules = db.query(Schedule).filter(Schedule.group_id == data.group_id,
                                              Schedule.subject_id == data.subject_id).all()
        for s in schedules:
            clash = db.query(Schedule).filter(
                Schedule.teacher_id == data.teacher_id, Schedule.id != s.id,
                Schedule.day_of_week == s.day_of_week,
                Schedule.start_time < s.end_time, Schedule.end_time > s.start_time).first()
            if clash:
                raise HTTPException(status_code=409,
                                    detail="Yangi o'qituvchining boshqa darsi shu vaqtga to'g'ri keladi")
            s.teacher_id = data.teacher_id
        obj.teacher_id = data.teacher_id

    _commit(db, "O'qituvchini tayinlab bo'lmadi")
    db.refresh(obj)
    return obj


def remove_teacher_assignment(db: Session, assignment_id: int) -> None:
    obj = _get_or_404(db, TeacherGroupSubject, assignment_id, "Tayinlash topilmadi")
    if db.query(Schedule).filter(Schedule.group_id == obj.group_id,
                                 Schedule.subject_id == obj.subject_id).first():
        raise HTTPException(status_code=409, detail="Avval bu fan bo'yicha dars jadvalini o'chiring")
    db.delete(obj)
    db.commit()
