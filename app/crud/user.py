from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.core.utils import generate_password, generate_username
from app.models import Group, GroupStudent, RoleEnum, Subject, TeacherSubject, User
from app.schemas.user import UserCreate, UserPreferencesUpdate, UserUpdate


def decorate_users(db: Session, users: list[User]) -> list[User]:
    """Admin ro'yxati uchun: o'quvchining sinfi va o'qituvchining fanlarini qo'shadi (2 ta so'rov)."""
    ids = [u.id for u in users]
    if not ids:
        return users

    groups = {sid: (gid, name) for sid, gid, name in
              db.query(GroupStudent.student_id, Group.id, Group.name)
              .join(Group, Group.id == GroupStudent.group_id)
              .filter(GroupStudent.student_id.in_(ids)).all()}
    subjects: dict[int, list[dict]] = {}
    for tid, subj in (db.query(TeacherSubject.teacher_id, Subject)
                      .join(Subject, Subject.id == TeacherSubject.subject_id)
                      .filter(TeacherSubject.teacher_id.in_(ids)).all()):
        subjects.setdefault(tid, []).append({"id": subj.id, "name": subj.name, "names": subj.names})

    for u in users:
        if u.id in groups:
            u.group_id, u.group_name = groups[u.id]
        if u.role == RoleEnum.teacher:
            u.subjects = subjects.get(u.id, [])
    return users


def get_user(db: Session, user_id: int) -> Optional[User]:
    user = db.get(User, user_id)
    if user is not None:
        decorate_users(db, [user])
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.strip().lower()).first()


def _users_query(db: Session, role: Optional[RoleEnum], is_active: Optional[bool],
                 search: Optional[str], group_id: Optional[int]):
    q = db.query(User)
    if role is not None:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    if group_id is not None:
        q = q.join(GroupStudent, GroupStudent.student_id == User.id).filter(GroupStudent.group_id == group_id)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(User.first_name.ilike(like), User.last_name.ilike(like),
                         User.username.ilike(like)))
    return q


def count_users(db: Session, role: Optional[RoleEnum] = None, is_active: Optional[bool] = None,
                search: Optional[str] = None, group_id: Optional[int] = None) -> int:
    return _users_query(db, role, is_active, search, group_id).count()


def get_users(db: Session, skip: int = 0, limit: int = 100, role: Optional[RoleEnum] = None,
              is_active: Optional[bool] = None, search: Optional[str] = None,
              group_id: Optional[int] = None):
    q = _users_query(db, role, is_active, search, group_id)
    return decorate_users(db, q.order_by(User.last_name, User.first_name, User.id).offset(skip).limit(limit).all())


def _unique_username(db: Session, first_name: str, last_name: str) -> str:
    """ali_valiyev band bo'lsa ali_valiyev_1, ali_valiyev_2 ..."""
    base = generate_username(first_name, last_name)
    username, counter = base, 0
    while get_user_by_username(db, username):
        counter += 1
        username = f"{base}_{counter}"
    return username


def create_user(db: Session, data: UserCreate) -> User:
    group_id = data.group_id
    if group_id is not None:
        if data.role != RoleEnum.pupil:
            raise HTTPException(status_code=400, detail="Faqat o'quvchini guruhga qo'shish mumkin")
        group = db.get(Group, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Guruh topilmadi")
        if not group.is_active:
            raise HTTPException(status_code=400, detail="Guruh faol emas")

    # Ikki so'rov bir vaqtda bir xil login olsa, unique cheklov ushlaydi va qayta uriniladi
    for _ in range(5):
        raw_password = generate_password()
        user = User(
            username=_unique_username(db, data.first_name, data.last_name),
            hashed_password=get_password_hash(raw_password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        if group_id is not None:
            db.add(GroupStudent(group_id=group_id, student_id=user.id))
        db.commit()
        db.refresh(user)
        user.generated_password = raw_password  # bazaga yozilmaydi, faqat javobda bir marta
        return user

    raise HTTPException(status_code=409, detail="Login yaratib bo'lmadi, qayta urinib ko'ring")


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def set_active(db: Session, user_id: int, active: bool, acting_admin_id: int) -> User:
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if not active:
        if user.id == acting_admin_id:
            raise HTTPException(status_code=400, detail="O'zingizni faolsizlantira olmaysiz")
        if user.role == RoleEnum.admin:
            raise HTTPException(status_code=400, detail="Adminni faolsizlantirib bo'lmaydi")
        user.token_version += 1  # amaldagi tokenlar darhol bekor bo'ladi
    user.is_active = active
    db.commit()
    db.refresh(user)
    return user


def reset_credentials(db: Session, user_id: int) -> User:
    """
    "Parolni yangilash": faqat parol yangilanadi, login o'zgarmaydi (eski login qaytariladi).
    Baholar, davomat va vazifalar saqlanib qoladi. Eski parol va eski tokenlar bekor bo'ladi.
    """
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.role == RoleEnum.admin:
        raise HTTPException(status_code=400, detail="Admin parolini bu yerdan yangilab bo'lmaydi")

    raw_password = generate_password()
    user.hashed_password = get_password_hash(raw_password)
    user.token_version += 1
    db.commit()
    db.refresh(user)
    user.generated_password = raw_password
    return user


def update_preferences(db: Session, user: User, data: UserPreferencesUpdate) -> User:
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
