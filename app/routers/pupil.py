import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_pupil
from app.crud import academic as crud_academic
from app.crud import assignment as crud_assignment
from app.crud import attendance as crud_attendance
from app.crud import grade as crud_grade
from app.crud import material as crud_material
from app.crud import schedule as crud_schedule
from app.database import get_db
from app.models import User
from app.schemas.assignment import HomeworkResponse, SubmissionCreate, SubmissionResponse
from app.schemas.attendance import AttendanceResponse
from app.schemas.grade import GradeResponse
from app.schemas.material import MaterialResponse
from app.schemas.schedule import ScheduleResponse

router = APIRouter(prefix="/pupil", tags=["O'quvchi paneli"],
                   dependencies=[Depends(get_current_pupil)])


@router.get("/my-schedules/", response_model=List[ScheduleResponse])
def my_schedules(db: Session = Depends(get_db), pupil: User = Depends(get_current_pupil)):
    group_id = crud_academic.get_pupil_group_id(db, pupil.id)
    if group_id is None:
        return []
    return crud_schedule.get_schedules(db, group_id=group_id)


@router.get("/my-grades/", response_model=List[GradeResponse])
def my_grades(subject_id: Optional[int] = None, date_from: Optional[dt.date] = None,
              date_to: Optional[dt.date] = None, db: Session = Depends(get_db),
              pupil: User = Depends(get_current_pupil)):
    return crud_grade.list_grades(db, student_id=pupil.id, subject_id=subject_id,
                                  date_from=date_from, date_to=date_to)


@router.get("/my-attendance/", response_model=List[AttendanceResponse])
def my_attendance(date_from: Optional[dt.date] = None, date_to: Optional[dt.date] = None,
                  db: Session = Depends(get_db), pupil: User = Depends(get_current_pupil)):
    return crud_attendance.get_student_attendance(db, pupil.id, date_from, date_to)


@router.get("/homeworks/", response_model=List[HomeworkResponse])
def my_homeworks(subject_id: Optional[int] = None, db: Session = Depends(get_db),
                 pupil: User = Depends(get_current_pupil)):
    return crud_assignment.list_pupil_homeworks(db, pupil, subject_id)


@router.post("/homeworks/{homework_id}/submit", response_model=SubmissionResponse)
def submit_homework(homework_id: int, data: SubmissionCreate, db: Session = Depends(get_db),
                    pupil: User = Depends(get_current_pupil)):
    """Vazifani topshiradi. Muddat tugamaguncha va baholanmaguncha qayta yuborish mumkin."""
    return crud_assignment.submit_homework(db, pupil, homework_id, data)


@router.get("/my-submissions/", response_model=List[SubmissionResponse])
def my_submissions(db: Session = Depends(get_db), pupil: User = Depends(get_current_pupil)):
    return crud_assignment.list_pupil_submissions(db, pupil)


@router.get("/materials/", response_model=List[MaterialResponse])
def materials(subject_id: Optional[int] = None, material_type: Optional[str] = None,
              db: Session = Depends(get_db), pupil: User = Depends(get_current_pupil)):
    return crud_material.list_pupil_materials(db, pupil, subject_id, material_type)
