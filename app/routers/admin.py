from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.crud import academic as crud_academic
from app.crud import schedule as crud_schedule
from app.crud import user as crud_user
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.academic import (GroupCreate, GroupResponse, GroupSubjectResponse, GroupUpdate,
                                  PupilRef, SubjectCreate, SubjectRef, SubjectResponse,
                                  SubjectUpdate, TeacherAssign, TeacherAssignmentResponse,
                                  TeacherSubjectResponse)
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin", tags=["Administrator paneli"],
                   dependencies=[Depends(get_current_admin)])


# ==================== FOYDALANUVCHILAR ====================
@router.post("/users/", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """O'qituvchi yoki o'quvchi yaratish. Login va parol avtomatik, parol faqat shu javobda ko'rinadi."""
    return crud_user.create_user(db, data)


@router.get("/users/", response_model=List[UserResponse])
def list_users(response: Response, skip: int = 0, limit: int = 20, role: Optional[RoleEnum] = None,
               is_active: Optional[bool] = None, search: Optional[str] = None,
               group_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Sahifalab qaytaradi. Jami soni X-Total-Count sarlavhasida."""
    response.headers["X-Total-Count"] = str(crud_user.count_users(db, role, is_active, search, group_id))
    return crud_user.get_users(db, skip, limit, role, is_active, search, group_id)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud_user.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    return crud_user.update_user(db, user_id, data)


@router.put("/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: int, db: Session = Depends(get_db),
                    admin: User = Depends(get_current_admin)):
    return crud_user.set_active(db, user_id, False, admin.id)


@router.put("/users/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: int, db: Session = Depends(get_db),
                  admin: User = Depends(get_current_admin)):
    return crud_user.set_active(db, user_id, True, admin.id)


@router.put("/users/{user_id}/reset-password", response_model=UserResponse)
def reset_password(user_id: int, db: Session = Depends(get_db)):
    """"Parolni yangilash: faqat parol yangilanadi, login o'zgarmaydi."""
    return crud_user.reset_credentials(db, user_id)


# ==================== FANLAR ====================
@router.post("/subjects/", response_model=SubjectResponse, status_code=201)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    return crud_academic.create_subject(db, data)


@router.get("/subjects/", response_model=List[SubjectResponse])
def list_subjects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_academic.get_subjects(db, skip, limit)


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, data: SubjectUpdate, db: Session = Depends(get_db)):
    return crud_academic.update_subject(db, subject_id, data)


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    crud_academic.delete_subject(db, subject_id)
    return {"message": "Fan o'chirildi"}


# ==================== GURUHLAR (SINFLAR) ====================
@router.post("/groups/", response_model=GroupResponse, status_code=201)
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    return crud_academic.create_group(db, data)


@router.get("/groups/", response_model=List[GroupResponse])
def list_groups(skip: int = 0, limit: int = 100, is_active: Optional[bool] = None,
                db: Session = Depends(get_db)):
    return crud_academic.get_groups(db, skip, limit, is_active)


@router.put("/groups/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    return crud_academic.update_group(db, group_id, data)


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    crud_academic.delete_group(db, group_id)
    return {"message": "Guruh o'chirildi"}


# ---- guruh o'quvchilari ----
@router.get("/groups/{group_id}/pupils", response_model=List[UserResponse])
def group_pupils(group_id: int, db: Session = Depends(get_db)):
    return crud_academic.get_group_pupils(db, group_id)


@router.post("/groups/{group_id}/pupils")
def add_pupil(group_id: int, data: PupilRef, db: Session = Depends(get_db)):
    """O'quvchini guruhga qo'shadi (boshqa guruhda bo'lsa ko'chiradi)."""
    crud_academic.add_pupil_to_group(db, group_id, data.pupil_id)
    return {"message": "O'quvchi guruhga qo'shildi"}


@router.delete("/groups/{group_id}/pupils/{pupil_id}")
def remove_pupil(group_id: int, pupil_id: int, db: Session = Depends(get_db)):
    crud_academic.remove_pupil_from_group(db, group_id, pupil_id)
    return {"message": "O'quvchi guruhdan chiqarildi"}


# ---- guruh fanlari ----
@router.get("/groups/{group_id}/subjects", response_model=List[GroupSubjectResponse])
def group_subjects(group_id: int, db: Session = Depends(get_db)):
    return crud_academic.list_group_subjects(db, group_id)


@router.post("/groups/{group_id}/subjects", response_model=GroupSubjectResponse, status_code=201)
def add_group_subject(group_id: int, data: SubjectRef, db: Session = Depends(get_db)):
    return crud_academic.add_subject_to_group(db, group_id, data.subject_id)


@router.delete("/groups/{group_id}/subjects/{subject_id}")
def remove_group_subject(group_id: int, subject_id: int, db: Session = Depends(get_db)):
    crud_academic.remove_subject_from_group(db, group_id, subject_id)
    return {"message": "Fan guruhdan olib tashlandi"}


# ==================== O'QITUVCHI FANLARI ====================
@router.get("/teachers/{teacher_id}/subjects", response_model=List[TeacherSubjectResponse])
def teacher_subjects(teacher_id: int, db: Session = Depends(get_db)):
    return crud_academic.list_teacher_subjects(db, teacher_id)


@router.post("/teachers/{teacher_id}/subjects", response_model=TeacherSubjectResponse, status_code=201)
def add_teacher_subject(teacher_id: int, data: SubjectRef, db: Session = Depends(get_db)):
    return crud_academic.add_subject_to_teacher(db, teacher_id, data.subject_id)


@router.delete("/teachers/{teacher_id}/subjects/{subject_id}")
def remove_teacher_subject(teacher_id: int, subject_id: int, db: Session = Depends(get_db)):
    crud_academic.remove_subject_from_teacher(db, teacher_id, subject_id)
    return {"message": "Fan o'qituvchidan olib tashlandi"}


# ==================== O'QITUVCHI TAYINLASH (guruh + fan) ====================
@router.get("/assignments/", response_model=List[TeacherAssignmentResponse])
def list_assignments(teacher_id: Optional[int] = None, group_id: Optional[int] = None,
                     db: Session = Depends(get_db)):
    return crud_academic.list_teacher_assignments(db, teacher_id, group_id)


@router.post("/assignments/", response_model=TeacherAssignmentResponse, status_code=201)
def assign_teacher(data: TeacherAssign, db: Session = Depends(get_db)):
    """Guruhdagi fanni o'qituvchiga tayinlaydi. Oldin fan guruhga va o'qituvchiga biriktirilgan bo'lishi kerak."""
    return crud_academic.assign_teacher(db, data)


@router.delete("/assignments/{assignment_id}")
def remove_assignment(assignment_id: int, db: Session = Depends(get_db)):
    crud_academic.remove_teacher_assignment(db, assignment_id)
    return {"message": "Tayinlash o'chirildi"}


# ==================== DARS JADVALI ====================
@router.post("/schedules/", response_model=ScheduleResponse, status_code=201)
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    return crud_schedule.create_schedule(db, data)


@router.get("/schedules/", response_model=List[ScheduleResponse])
def list_schedules(skip: int = 0, limit: int = 200, group_id: Optional[int] = None,
                   teacher_id: Optional[int] = None, day_of_week: Optional[int] = None,
                   db: Session = Depends(get_db)):
    return crud_schedule.get_schedules(db, skip, limit, group_id, teacher_id, day_of_week)


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, data: ScheduleUpdate, db: Session = Depends(get_db)):
    return crud_schedule.update_schedule(db, schedule_id, data)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    crud_schedule.delete_schedule(db, schedule_id)
    return {"message": "Dars jadvali o'chirildi"}
