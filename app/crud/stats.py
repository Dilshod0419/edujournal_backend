"""Statistika hisob-kitoblari (admin, o'qituvchi, o'quvchi uchun)."""
import calendar
import datetime as dt
from collections import defaultdict
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import MAX_SCORE
from app.core.utils import get_tz, today_local
from app.models import (Attendance, Grade, Group, GroupStudent, Homework, HomeworkSubmission,
                        RoleEnum, Schedule, Subject, TeacherGroupSubject, User)

STATUSES = ("present", "late", "absent", "excused")


# ---------------------------------------------------------------- yordamchilar

def resolve_period(period: str, ref: Optional[dt.date] = None):
    """day | month | year | all  ->  (date_from, date_to)"""
    ref = ref or today_local()
    if period == "day":
        return ref, ref
    if period == "month":
        last = calendar.monthrange(ref.year, ref.month)[1]
        return ref.replace(day=1), ref.replace(day=last)
    if period == "year":
        return dt.date(ref.year, 1, 1), dt.date(ref.year, 12, 31)
    return None, None  # all


def _bounds(date_from: Optional[dt.date], date_to: Optional[dt.date]):
    """Sanalarni Toshkent vaqti bo'yicha datetime chegaralariga aylantiradi."""
    tz = get_tz()
    lo = dt.datetime.combine(date_from, dt.time.min, tzinfo=tz) if date_from else None
    hi = dt.datetime.combine(date_to, dt.time.max, tzinfo=tz) if date_to else None
    return lo, hi


def _att_filter(q, date_from, date_to):
    if date_from:
        q = q.filter(Attendance.date >= date_from)
    if date_to:
        q = q.filter(Attendance.date <= date_to)
    return q


def _grade_filter(q, date_from, date_to):
    if date_from:
        q = q.filter(Grade.date >= date_from)
    if date_to:
        q = q.filter(Grade.date <= date_to)
    return q


def _hw_filter(q, date_from, date_to):
    lo, hi = _bounds(date_from, date_to)
    if lo:
        q = q.filter(Homework.deadline >= lo)
    if hi:
        q = q.filter(Homework.deadline <= hi)
    return q


def _names(uz, ru, en) -> dict:
    return {"uz": uz, "ru": ru or uz, "en": en or uz}


def _status_value(s) -> str:
    return getattr(s, "value", s)


def att_summary(counts: dict) -> dict:
    counts = {k: int(counts.get(k, 0)) for k in STATUSES}
    total = sum(counts.values())
    attended = counts["present"] + counts["late"]
    return {**counts, "total": total,
            "rate": round(attended / total * 100, 1) if total else None}


def _avg(values) -> Optional[float]:
    values = list(values)
    return round(sum(values) / len(values), 2) if values else None


def activity_score(attendance_rate, avg_grade, submission_rate) -> Optional[float]:
    """Faollik = davomat %, o'rtacha baho (%) va vazifa topshirish % ning o'rtachasi."""
    parts = []
    if attendance_rate is not None:
        parts.append(attendance_rate)
    if avg_grade is not None:
        parts.append(avg_grade / MAX_SCORE * 100)
    if submission_rate is not None:
        parts.append(submission_rate)
    return round(sum(parts) / len(parts), 1) if parts else None


def _rate(done: int, expected: int) -> Optional[float]:
    return round(min(done / expected * 100, 100), 1) if expected else None


# ---------------------------------------------------------------- ADMIN

def admin_overview(db: Session) -> dict:
    today = today_local()
    month_from, month_to = resolve_period("month", today)

    def count(role):
        return db.query(func.count(User.id)).filter(User.role == role, User.is_active.is_(True)).scalar()

    today_counts = defaultdict(int)
    for status, n in _att_filter(
            db.query(Attendance.status, func.count(Attendance.id)), today, today
    ).group_by(Attendance.status).all():
        today_counts[_status_value(status)] = n

    avg_grade = _grade_filter(db.query(func.avg(Grade.score)), month_from, month_to).scalar()
    return {
        "pupils": count(RoleEnum.pupil),
        "teachers": count(RoleEnum.teacher),
        "groups": db.query(func.count(Group.id)).filter(Group.is_active.is_(True)).scalar(),
        "schedules": db.query(func.count(Schedule.id)).scalar(),
        "today_attendance": att_summary(today_counts),
        "month_avg_grade": round(float(avg_grade), 2) if avg_grade is not None else None,
    }


def admin_groups(db: Session, date_from: Optional[dt.date], date_to: Optional[dt.date]) -> list[dict]:
    """Har bir sinf bo'yicha faollik: davomat, baho, vazifa topshirish."""
    groups = db.query(Group).order_by(Group.name).all()

    pupils = dict(db.query(GroupStudent.group_id, func.count(GroupStudent.id))
                  .group_by(GroupStudent.group_id).all())

    att: dict[int, dict] = defaultdict(lambda: defaultdict(int))
    q = (db.query(Schedule.group_id, Attendance.status, func.count(Attendance.id))
         .join(Schedule, Schedule.id == Attendance.schedule_id))
    for gid, status, n in _att_filter(q, date_from, date_to).group_by(
            Schedule.group_id, Attendance.status).all():
        att[gid][_status_value(status)] += n

    q = (db.query(GroupStudent.group_id, func.avg(Grade.score), func.count(Grade.id))
         .join(GroupStudent, GroupStudent.student_id == Grade.student_id))
    grades = {gid: (avg, n) for gid, avg, n in
              _grade_filter(q, date_from, date_to).group_by(GroupStudent.group_id).all()}

    hw_total = dict(_hw_filter(db.query(Homework.group_id, func.count(Homework.id)), date_from, date_to)
                    .group_by(Homework.group_id).all())
    q = (db.query(Homework.group_id, func.count(HomeworkSubmission.id))
         .join(HomeworkSubmission, HomeworkSubmission.homework_id == Homework.id))
    hw_done = dict(_hw_filter(q, date_from, date_to).group_by(Homework.group_id).all())

    rows = []
    for g in groups:
        a = att_summary(att.get(g.id, {}))
        avg, n = grades.get(g.id, (None, 0))
        avg = round(float(avg), 2) if avg is not None else None
        sub_rate = _rate(hw_done.get(g.id, 0), hw_total.get(g.id, 0) * pupils.get(g.id, 0))
        rows.append({
            "group_id": g.id, "group_name": g.name, "is_active": g.is_active,
            "pupils": pupils.get(g.id, 0),
            "attendance": a, "attendance_rate": a["rate"],
            "avg_grade": avg, "grades_count": n,
            "homeworks": hw_total.get(g.id, 0), "submission_rate": sub_rate,
            "activity": activity_score(a["rate"], avg, sub_rate),
        })
    return rows


def admin_attendance_trend(db: Session, days: int = 30) -> list[dict]:
    end = today_local()
    start = end - dt.timedelta(days=days - 1)
    per_day: dict[dt.date, dict] = defaultdict(lambda: defaultdict(int))
    for day, status, n in _att_filter(
            db.query(Attendance.date, Attendance.status, func.count(Attendance.id)), start, end
    ).group_by(Attendance.date, Attendance.status).all():
        per_day[day][_status_value(status)] += n
    out = []
    for day in sorted(per_day):
        s = att_summary(per_day[day])
        out.append({"date": day.isoformat(), **s})
    return out


# ---------------------------------------------------------------- TEACHER

def _teacher_scope(db: Session, teacher: User, group_id, subject_id):
    q = db.query(TeacherGroupSubject).filter(TeacherGroupSubject.teacher_id == teacher.id)
    if group_id is not None:
        q = q.filter(TeacherGroupSubject.group_id == group_id)
    if subject_id is not None:
        q = q.filter(TeacherGroupSubject.subject_id == subject_id)
    return q.all()


def teacher_stats(db: Session, teacher: User, group_id: Optional[int], subject_id: Optional[int],
                  date_from: Optional[dt.date], date_to: Optional[dt.date]) -> dict:
    scope = _teacher_scope(db, teacher, group_id, subject_id)
    group_ids = sorted({t.group_id for t in scope})
    empty = {"summary": {"pupils": 0, "attendance": att_summary({}), "avg_grade": None,
                         "grades_count": 0, "submission_rate": None, "activity": None},
             "pupils": [], "trend": []}
    if not group_ids:
        return empty

    subj_ids = sorted({t.subject_id for t in scope})

    # o'quvchilar
    pupils = (db.query(User, GroupStudent.group_id, Group.name)
              .join(GroupStudent, GroupStudent.student_id == User.id)
              .join(Group, Group.id == GroupStudent.group_id)
              .filter(GroupStudent.group_id.in_(group_ids))
              .order_by(Group.name, User.last_name, User.first_name).all())

    # davomat (faqat shu o'qituvchining darslari)
    q = (db.query(Attendance.student_id, Attendance.status, func.count(Attendance.id))
         .join(Schedule, Schedule.id == Attendance.schedule_id)
         .filter(Schedule.teacher_id == teacher.id, Schedule.group_id.in_(group_ids),
                 Schedule.subject_id.in_(subj_ids)))
    att: dict[int, dict] = defaultdict(lambda: defaultdict(int))
    for sid, status, n in _att_filter(q, date_from, date_to).group_by(
            Attendance.student_id, Attendance.status).all():
        att[sid][_status_value(status)] += n

    # baholar (faqat shu o'qituvchi qo'ygan)
    q = (db.query(Grade.student_id, func.avg(Grade.score), func.count(Grade.id))
         .filter(Grade.teacher_id == teacher.id, Grade.subject_id.in_(subj_ids)))
    grades = {sid: (avg, n) for sid, avg, n in
              _grade_filter(q, date_from, date_to).group_by(Grade.student_id).all()}

    # vazifalar
    hw_q = db.query(Homework.group_id, func.count(Homework.id)).filter(
        Homework.teacher_id == teacher.id, Homework.group_id.in_(group_ids),
        Homework.subject_id.in_(subj_ids))
    hw_total = dict(_hw_filter(hw_q, date_from, date_to).group_by(Homework.group_id).all())
    sub_q = (db.query(HomeworkSubmission.student_id, func.count(HomeworkSubmission.id),
                      func.avg(HomeworkSubmission.score))
             .join(Homework, Homework.id == HomeworkSubmission.homework_id)
             .filter(Homework.teacher_id == teacher.id, Homework.group_id.in_(group_ids),
                     Homework.subject_id.in_(subj_ids)))
    subs = {sid: (n, avg) for sid, n, avg in
            _hw_filter(sub_q, date_from, date_to).group_by(HomeworkSubmission.student_id).all()}

    rows = []
    total_att: dict = defaultdict(int)
    all_scores_sum, all_scores_n = 0.0, 0
    sub_done_total, sub_expected_total = 0, 0
    for user, gid, gname in pupils:
        a = att_summary(att.get(user.id, {}))
        for k in STATUSES:
            total_att[k] += a[k]
        avg, n = grades.get(user.id, (None, 0))
        avg = round(float(avg), 2) if avg is not None else None
        if avg is not None:
            all_scores_sum += avg * n
            all_scores_n += n
        done, hw_avg = subs.get(user.id, (0, None))
        expected = hw_total.get(gid, 0)
        sub_done_total += min(done, expected)
        sub_expected_total += expected
        rows.append({
            "student_id": user.id, "student_name": user.full_name,
            "group_id": gid, "group_name": gname,
            "attendance": a, "attendance_rate": a["rate"],
            "avg_grade": avg, "grades_count": n,
            "homeworks": expected, "submitted": done,
            "submission_rate": _rate(done, expected),
            "homework_avg": round(float(hw_avg), 2) if hw_avg is not None else None,
        })

    # kunlar bo'yicha dinamika
    trend_att: dict[dt.date, dict] = defaultdict(lambda: defaultdict(int))
    q = (db.query(Attendance.date, Attendance.status, func.count(Attendance.id))
         .join(Schedule, Schedule.id == Attendance.schedule_id)
         .filter(Schedule.teacher_id == teacher.id, Schedule.group_id.in_(group_ids),
                 Schedule.subject_id.in_(subj_ids)))
    for day, status, n in _att_filter(q, date_from, date_to).group_by(
            Attendance.date, Attendance.status).all():
        trend_att[day][_status_value(status)] += n
    trend_gr = {}
    q = (db.query(Grade.date, func.avg(Grade.score))
         .filter(Grade.teacher_id == teacher.id, Grade.subject_id.in_(subj_ids)))
    for day, avg in _grade_filter(q, date_from, date_to).group_by(Grade.date).all():
        trend_gr[day] = round(float(avg), 2)
    trend = [{"date": d.isoformat(), "attendance_rate": att_summary(trend_att[d])["rate"] if d in trend_att else None,
              "avg_grade": trend_gr.get(d)} for d in sorted(set(trend_att) | set(trend_gr))]

    att_total = att_summary(total_att)
    avg_all = round(all_scores_sum / all_scores_n, 2) if all_scores_n else None
    sub_rate = _rate(sub_done_total, sub_expected_total)
    return {
        "summary": {"pupils": len(rows), "attendance": att_total, "avg_grade": avg_all,
                    "grades_count": all_scores_n, "submission_rate": sub_rate,
                    "activity": activity_score(att_total["rate"], avg_all, sub_rate)},
        "pupils": rows, "trend": trend,
    }


def teacher_attendance_rows(db: Session, teacher: User, group_id, subject_id, date_from, date_to):
    q = (db.query(Attendance.date, Group.name, Subject.name, Subject.name_ru, Subject.name_en,
                  User.last_name, User.first_name, Attendance.status)
         .join(Schedule, Schedule.id == Attendance.schedule_id)
         .join(Group, Group.id == Schedule.group_id)
         .join(Subject, Subject.id == Schedule.subject_id)
         .join(User, User.id == Attendance.student_id)
         .filter(Schedule.teacher_id == teacher.id))
    if group_id is not None:
        q = q.filter(Schedule.group_id == group_id)
    if subject_id is not None:
        q = q.filter(Schedule.subject_id == subject_id)
    q = _att_filter(q, date_from, date_to).order_by(Attendance.date, Group.name, User.last_name)
    return [{"date": d, "group": g, "subject": s, "subject_names": _names(s, sr, se),
             "student": f"{fn} {ln}", "status": _status_value(st)}
            for d, g, s, sr, se, ln, fn, st in q.all()]


def teacher_grade_rows(db: Session, teacher: User, group_id, subject_id, date_from, date_to):
    q = (db.query(Grade.date, Group.name, Subject.name, Subject.name_ru, Subject.name_en,
                  User.last_name, User.first_name, Grade.score, Grade.grade_type, Grade.comment)
         .join(User, User.id == Grade.student_id)
         .join(GroupStudent, GroupStudent.student_id == Grade.student_id)
         .join(Group, Group.id == GroupStudent.group_id)
         .join(Subject, Subject.id == Grade.subject_id)
         .filter(Grade.teacher_id == teacher.id))
    if group_id is not None:
        q = q.filter(GroupStudent.group_id == group_id)
    if subject_id is not None:
        q = q.filter(Grade.subject_id == subject_id)
    q = _grade_filter(q, date_from, date_to).order_by(Grade.date, Group.name, User.last_name)
    return [{"date": d, "group": g, "subject": s, "subject_names": _names(s, sr, se),
             "student": f"{fn} {ln}", "score": sc, "type": t, "comment": c or ""}
            for d, g, s, sr, se, ln, fn, sc, t, c in q.all()]


# ---------------------------------------------------------------- PUPIL

def _bucket(day: dt.date, period: str) -> str:
    return day.isoformat() if period in ("day", "month") else day.strftime("%Y-%m")


def pupil_rows(db: Session, pupil: User, date_from, date_to):
    """Eksport va statistika uchun xom ma'lumotlar."""
    g_q = (db.query(Grade.date, Subject.name, Subject.name_ru, Subject.name_en, Grade.score,
                    Grade.grade_type, Grade.comment, Grade.subject_id)
           .join(Subject, Subject.id == Grade.subject_id).filter(Grade.student_id == pupil.id))
    grades = [{"date": d, "subject": s, "subject_names": _names(s, sr, se), "score": sc, "type": t,
               "comment": c or "", "subject_id": sid}
              for d, s, sr, se, sc, t, c, sid in _grade_filter(g_q, date_from, date_to).order_by(Grade.date).all()]

    a_q = (db.query(Attendance.date, Subject.name, Subject.name_ru, Subject.name_en, Attendance.status)
           .join(Schedule, Schedule.id == Attendance.schedule_id)
           .join(Subject, Subject.id == Schedule.subject_id).filter(Attendance.student_id == pupil.id))
    attendance = [{"date": d, "subject": s, "subject_names": _names(s, sr, se), "status": _status_value(st)}
                  for d, s, sr, se, st in _att_filter(a_q, date_from, date_to).order_by(Attendance.date).all()]

    link = db.query(GroupStudent).filter(GroupStudent.student_id == pupil.id).first()
    homeworks = []
    if link:
        h_q = (db.query(Homework, HomeworkSubmission)
               .outerjoin(HomeworkSubmission, (HomeworkSubmission.homework_id == Homework.id)
                          & (HomeworkSubmission.student_id == pupil.id))
               .filter(Homework.group_id == link.group_id))
        for hw, sub in _hw_filter(h_q, date_from, date_to).order_by(Homework.deadline).all():
            homeworks.append({"title": hw.title, "subject": hw.subject.name,
                              "subject_names": hw.subject.names, "deadline": hw.deadline,
                              "submitted": sub is not None,
                              "submitted_at": sub.submitted_at if sub else None,
                              "score": sub.score if sub else None})
    return grades, attendance, homeworks


def pupil_stats(db: Session, pupil: User, period: str, ref: Optional[dt.date]) -> dict:
    date_from, date_to = resolve_period(period, ref)
    grades, attendance, homeworks = pupil_rows(db, pupil, date_from, date_to)

    link = (db.query(GroupStudent, Group).join(Group, Group.id == GroupStudent.group_id)
            .filter(GroupStudent.student_id == pupil.id).first())

    # baholar
    scores = [g["score"] for g in grades]
    by_subject: dict[str, list[int]] = defaultdict(list)
    subject_names: dict[str, dict] = {}
    for g in grades:
        by_subject[g["subject"]].append(g["score"])
        subject_names[g["subject"]] = g["subject_names"]
    distribution = {str(s): scores.count(s) for s in range(2, MAX_SCORE + 1)}

    # davomat
    counts: dict = defaultdict(int)
    for a in attendance:
        counts[a["status"]] += 1
    att = att_summary(counts)

    # vazifalar
    hw_scores = [h["score"] for h in homeworks if h["score"] is not None]
    hw = {"total": len(homeworks), "submitted": sum(1 for h in homeworks if h["submitted"]),
          "graded": len(hw_scores), "avg_score": _avg(hw_scores)}
    hw["rate"] = _rate(hw["submitted"], hw["total"])

    # dinamika
    series_g: dict[str, list[int]] = defaultdict(list)
    series_a: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for g in grades:
        series_g[_bucket(g["date"], period)].append(g["score"])
    for a in attendance:
        series_a[_bucket(a["date"], period)][a["status"]] += 1
    series = [{"label": k, "avg_grade": _avg(series_g[k]) if k in series_g else None,
               "grades_count": len(series_g.get(k, [])),
               "attendance_rate": att_summary(series_a[k])["rate"] if k in series_a else None}
              for k in sorted(set(series_g) | set(series_a))]

    avg_grade = _avg(scores)
    return {
        "period": period,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "group_name": link[1].name if link else None,
        "grades": {"count": len(scores), "avg": avg_grade, "min": min(scores) if scores else None,
                   "max": max(scores) if scores else None, "distribution": distribution,
                   "by_subject": [{"subject": k, "names": subject_names[k], "avg": _avg(v), "count": len(v)}
                                  for k, v in sorted(by_subject.items())]},
        "attendance": att,
        "homework": hw,
        "activity": activity_score(att["rate"], avg_grade, hw["rate"]),
        "series": series,
    }
