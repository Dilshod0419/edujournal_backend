import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core import excel
from app.core.deps import get_current_admin, get_current_pupil, get_current_teacher
from app.crud import stats as crud_stats
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/stats", tags=["Statistika"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content=content, media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _range(period: str, ref: Optional[dt.date], date_from, date_to):
    """Agar date_from/date_to berilsa ular ishlatiladi, aks holda period bo'yicha."""
    if date_from or date_to:
        return date_from, date_to
    return crud_stats.resolve_period(period, ref)


# ==================== ADMIN ====================
@router.get("/admin/overview")
def admin_overview(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return crud_stats.admin_overview(db)


@router.get("/admin/groups")
def admin_groups(period: str = Query("month", pattern="^(day|month|year|all)$"),
                 ref: Optional[dt.date] = None, date_from: Optional[dt.date] = None,
                 date_to: Optional[dt.date] = None, db: Session = Depends(get_db),
                 _: User = Depends(get_current_admin)):
    lo, hi = _range(period, ref, date_from, date_to)
    return {"date_from": lo, "date_to": hi, "groups": crud_stats.admin_groups(db, lo, hi)}


@router.get("/admin/trend")
def admin_trend(days: int = Query(30, ge=7, le=365), db: Session = Depends(get_db),
                _: User = Depends(get_current_admin)):
    return crud_stats.admin_attendance_trend(db, days)


@router.get("/admin/groups/export")
def admin_groups_export(period: str = Query("month", pattern="^(day|month|year|all)$"),
                        ref: Optional[dt.date] = None, date_from: Optional[dt.date] = None,
                        date_to: Optional[dt.date] = None, lang: str = "uz",
                        db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    lo, hi = _range(period, ref, date_from, date_to)
    rows = crud_stats.admin_groups(db, lo, hi)
    return _xlsx(excel.groups_workbook(rows, lang), "sinflar_statistikasi.xlsx")


# ==================== TEACHER ====================
@router.get("/teacher")
def teacher_stats(group_id: Optional[int] = None, subject_id: Optional[int] = None,
                  period: str = Query("month", pattern="^(day|month|year|all)$"),
                  ref: Optional[dt.date] = None, date_from: Optional[dt.date] = None,
                  date_to: Optional[dt.date] = None, db: Session = Depends(get_db),
                  teacher: User = Depends(get_current_teacher)):
    lo, hi = _range(period, ref, date_from, date_to)
    return crud_stats.teacher_stats(db, teacher, group_id, subject_id, lo, hi)


@router.get("/teacher/export")
def teacher_export(group_id: Optional[int] = None, subject_id: Optional[int] = None,
                   period: str = Query("month", pattern="^(day|month|year|all)$"),
                   ref: Optional[dt.date] = None, date_from: Optional[dt.date] = None,
                   date_to: Optional[dt.date] = None, lang: str = "uz",
                   db: Session = Depends(get_db), teacher: User = Depends(get_current_teacher)):
    lo, hi = _range(period, ref, date_from, date_to)
    stats = crud_stats.teacher_stats(db, teacher, group_id, subject_id, lo, hi)
    att = crud_stats.teacher_attendance_rows(db, teacher, group_id, subject_id, lo, hi)
    grades = crud_stats.teacher_grade_rows(db, teacher, group_id, subject_id, lo, hi)
    return _xlsx(excel.teacher_workbook(stats, att, grades, lang), "oqituvchi_statistikasi.xlsx")


# ==================== PUPIL ====================
@router.get("/pupil")
def pupil_stats(period: str = Query("month", pattern="^(day|month|year|all)$"),
                ref: Optional[dt.date] = None, db: Session = Depends(get_db),
                pupil: User = Depends(get_current_pupil)):
    return crud_stats.pupil_stats(db, pupil, period, ref)


@router.get("/pupil/export")
def pupil_export(period: str = Query("month", pattern="^(day|month|year|all)$"),
                 ref: Optional[dt.date] = None, lang: str = "uz", db: Session = Depends(get_db),
                 pupil: User = Depends(get_current_pupil)):
    stats = crud_stats.pupil_stats(db, pupil, period, ref)
    lo, hi = crud_stats.resolve_period(period, ref)
    grades, attendance, homeworks = crud_stats.pupil_rows(db, pupil, lo, hi)
    return _xlsx(excel.pupil_workbook(pupil.full_name, stats, grades, attendance, homeworks, lang),
                 "mening_natijalarim.xlsx")
