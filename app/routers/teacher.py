import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_teacher
from app.crud import academic as crud_academic
from app.crud import assignment as crud_assignment
from app.crud import attendance as crud_attendance
from app.crud import grade as crud_grade
from app.crud import material as crud_material
from app.crud import schedule as crud_schedule
from app.database import get_db
from app.models import User
from app.schemas.academic import TeacherAssignmentResponse, TeacherSubjectResponse
from app.schemas.assignment import (HomeworkCreate, HomeworkResponse, HomeworkUpdate,
                                    SubmissionGrade, SubmissionResponse)
from app.schemas.attendance import AttendanceBulkCreate, AttendanceResponse
from app.schemas.grade import GradeCreate, GradeResponse
from app.schemas.material import MaterialCreate, MaterialResponse, MaterialUpdate
from app.schemas.schedule import CurrentLessonResponse, ScheduleResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/teacher", tags=["O'qituvchi paneli"],
                   dependencies=[Depends(get_current_teacher)])


# ==================== DARSLAR ====================
@router.get("/my-classes/", response_model=List[TeacherAssignmentResponse])
def my_classes(db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    """Men qaysi guruhda qaysi fanni o'taman."""
    return crud_academic.list_teacher_assignments(db, teacher_id=teacher.id)


@router.get("/my-subjects/", response_model=List[TeacherSubjectResponse])
def my_subjects(db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    """Men o'ta oladigan fanlar (material qo'shishda kerak)."""
    return crud_academic.list_teacher_subjects(db, teacher.id)


@router.get("/groups/{group_id}/pupils", response_model=List[UserResponse])
def group_pupils(group_id: int, db: Session = Depends(get_db),
                 teacher: User = Depends(get_current_teacher)):
    """Men dars beradigan guruhning o'quvchilari (baholash uchun)."""
    if not crud_academic.list_teacher_assignments(db, teacher_id=teacher.id, group_id=group_id):
        raise HTTPException(status_code=403, detail="Siz bu guruhga dars bermaysiz")
    return crud_academic.get_group_pupils(db, group_id)


@router.get("/my-schedules/", response_model=List[ScheduleResponse])
def my_schedules(db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    return crud_schedule.get_schedules(db, teacher_id=teacher.id)


@router.get("/current-lesson/", response_model=CurrentLessonResponse)
def current_lesson(db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    """Tizimga kirganda: hozir qaysi guruhda qaysi fan o'tilishi va bugungi keyingi dars."""
    return crud_schedule.get_current_lesson(db, teacher.id)


@router.get("/schedules/{schedule_id}/pupils", response_model=List[UserResponse])
def schedule_pupils(schedule_id: int, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    """Davomat uchun dars guruhidagi o'quvchilar ro'yxati."""
    schedule = crud_schedule.get_teacher_schedule(db, teacher, schedule_id)
    return crud_academic.get_group_pupils(db, schedule.group_id)


# ==================== DAVOMAT ====================
@router.post("/attendance/", response_model=List[AttendanceResponse])
def mark_attendance(data: AttendanceBulkCreate, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    return crud_attendance.mark_attendance(db, teacher, data)


@router.get("/attendance/", response_model=List[AttendanceResponse])
def get_attendance(schedule_id: int, date: dt.date, db: Session = Depends(get_db),
                   teacher: User = Depends(get_current_teacher)):
    crud_schedule.get_teacher_schedule(db, teacher, schedule_id)
    return crud_attendance.get_attendance(db, schedule_id, date)


# ==================== UY VAZIFALARI ====================
@router.post("/homeworks/", response_model=HomeworkResponse, status_code=201)
def create_homework(data: HomeworkCreate, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    return crud_assignment.create_homework(db, teacher, data)


@router.get("/homeworks/", response_model=List[HomeworkResponse])
def list_homeworks(group_id: Optional[int] = None, subject_id: Optional[int] = None,
                   skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                   teacher: User = Depends(get_current_teacher)):
    return crud_assignment.list_teacher_homeworks(db, teacher, group_id, subject_id, skip, limit)


@router.put("/homeworks/{homework_id}", response_model=HomeworkResponse)
def update_homework(homework_id: int, data: HomeworkUpdate, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    return crud_assignment.update_homework(db, teacher, homework_id, data)


@router.delete("/homeworks/{homework_id}")
def delete_homework(homework_id: int, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    crud_assignment.delete_homework(db, teacher, homework_id)
    return {"message": "Uy vazifasi o'chirildi"}


@router.get("/homeworks/{homework_id}/submissions", response_model=List[SubmissionResponse])
def homework_submissions(homework_id: int, db: Session = Depends(get_db),
                         teacher: User = Depends(get_current_teacher)):
    return crud_assignment.list_submissions(db, teacher, homework_id)


@router.put("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
def grade_submission(submission_id: int, data: SubmissionGrade, db: Session = Depends(get_db),
                     teacher: User = Depends(get_current_teacher)):
    return crud_assignment.grade_submission(db, teacher, submission_id, data)


# ==================== BAHOLAR (dars davomidagi kunlik baholash) ====================
@router.post("/grades/", response_model=GradeResponse, status_code=201)
def add_grade(data: GradeCreate, db: Session = Depends(get_db),
              teacher: User = Depends(get_current_teacher)):
    """Baho bir marta qo'yiladi: keyin o'zgartirib yoki o'chirib bo'lmaydi."""
    return crud_grade.create_grade(db, teacher, data)


@router.get("/grades/", response_model=List[GradeResponse])
def list_grades(group_id: Optional[int] = None, subject_id: Optional[int] = None,
                student_id: Optional[int] = None, date_from: Optional[dt.date] = None,
                date_to: Optional[dt.date] = None, db: Session = Depends(get_db),
                teacher: User = Depends(get_current_teacher)):
    """Faqat o'zim qo'ygan baholar."""
    return crud_grade.list_grades(db, student_id=student_id, teacher_id=teacher.id,
                                  subject_id=subject_id, group_id=group_id,
                                  date_from=date_from, date_to=date_to)


# ==================== MATERIALLAR (termin, maqola, havola) ====================
@router.post("/materials/", response_model=MaterialResponse, status_code=201)
def create_material(data: MaterialCreate, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    return crud_material.create_material(db, teacher, data)


@router.get("/materials/", response_model=List[MaterialResponse])
def list_materials(subject_id: Optional[int] = None, skip: int = 0, limit: int = 100,
                   db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    return crud_material.list_teacher_materials(db, teacher, subject_id, skip, limit)


@router.put("/materials/{material_id}", response_model=MaterialResponse)
def update_material(material_id: int, data: MaterialUpdate, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    return crud_material.update_material(db, teacher, material_id, data)


@router.delete("/materials/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db),
                    teacher: User = Depends(get_current_teacher)):
    crud_material.delete_material(db, teacher, material_id)
    return {"message": "Material o'chirildi"}
