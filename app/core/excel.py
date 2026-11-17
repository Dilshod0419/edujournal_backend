"""Excel (.xlsx) hisobotlarini yasash. Sarlavhalar uz / ru / en tillarida."""
import datetime as dt
from io import BytesIO
from typing import Iterable, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

L = {
    "uz": {
        "group": "Sinf", "pupils": "O'quvchilar", "attendance": "Davomat %", "present": "Keldi",
        "absent": "Kelmadi", "late": "Kech qoldi", "excused": "Sababli", "avg": "O'rtacha baho",
        "grades": "Baholar soni", "homeworks": "Vazifalar", "submission": "Topshirish %",
        "activity": "Faollik %", "groups_sheet": "Sinflar", "student": "O'quvchi", "date": "Sana",
        "subject": "Fan", "status": "Holat", "score": "Baho", "type": "Turi", "comment": "Izoh",
        "submitted": "Topshirilgan", "hw_avg": "Vazifa bahosi", "summary": "Umumiy",
        "att_sheet": "Davomat jurnali", "grades_sheet": "Baholar", "hw_sheet": "Vazifalar",
        "pupils_sheet": "O'quvchilar", "deadline": "Muddat", "title": "Nomi", "yes": "Ha", "no": "Yo'q",
        "period": "Davr", "metric": "Ko'rsatkich", "value": "Qiymat", "total": "Jami",
        "from": "Boshlanish", "to": "Tugash", "all": "Barcha vaqt", "pupil": "O'quvchi",
        "daily": "Kunlik", "quiz": "Nazorat", "exam": "Imtihon",
    },
    "ru": {
        "group": "Класс", "pupils": "Ученики", "attendance": "Посещаемость %", "present": "Присутствовал",
        "absent": "Отсутствовал", "late": "Опоздал", "excused": "По уважительной", "avg": "Средний балл",
        "grades": "Кол-во оценок", "homeworks": "Задания", "submission": "Сдача %",
        "activity": "Активность %", "groups_sheet": "Классы", "student": "Ученик", "date": "Дата",
        "subject": "Предмет", "status": "Статус", "score": "Оценка", "type": "Тип", "comment": "Комментарий",
        "submitted": "Сдано", "hw_avg": "Оценка за задания", "summary": "Итоги",
        "att_sheet": "Журнал посещаемости", "grades_sheet": "Оценки", "hw_sheet": "Задания",
        "pupils_sheet": "Ученики", "deadline": "Срок", "title": "Название", "yes": "Да", "no": "Нет",
        "period": "Период", "metric": "Показатель", "value": "Значение", "total": "Всего",
        "from": "С", "to": "По", "all": "За всё время", "pupil": "Ученик",
        "daily": "Текущая", "quiz": "Контрольная", "exam": "Экзамен",
    },
    "en": {
        "group": "Class", "pupils": "Pupils", "attendance": "Attendance %", "present": "Present",
        "absent": "Absent", "late": "Late", "excused": "Excused", "avg": "Average grade",
        "grades": "Grades count", "homeworks": "Homework", "submission": "Submission %",
        "activity": "Activity %", "groups_sheet": "Classes", "student": "Pupil", "date": "Date",
        "subject": "Subject", "status": "Status", "score": "Grade", "type": "Type", "comment": "Comment",
        "submitted": "Submitted", "hw_avg": "Homework grade", "summary": "Summary",
        "att_sheet": "Attendance log", "grades_sheet": "Grades", "hw_sheet": "Homework",
        "pupils_sheet": "Pupils", "deadline": "Deadline", "title": "Title", "yes": "Yes", "no": "No",
        "period": "Period", "metric": "Metric", "value": "Value", "total": "Total",
        "from": "From", "to": "To", "all": "All time", "pupil": "Pupil",
        "daily": "Daily", "quiz": "Quiz", "exam": "Exam",
    },
}

HEADER_FILL = PatternFill("solid", fgColor="2563EB")
HEADER_FONT = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="D1D5DB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def labels(lang: str) -> dict:
    return L.get(lang, L["uz"])


def _fmt(value):
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def _sheet(wb: Workbook, title: str, headers: list, rows: Iterable[list], first: bool = False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    n = 0
    for row in rows:
        ws.append([_fmt(v) for v in row])
        n += 1
    for r in ws.iter_rows(min_row=2, max_row=n + 1):
        for cell in r:
            cell.border = BORDER
    for idx, header in enumerate(headers, start=1):
        width = max([len(str(header))] + [len(str(ws.cell(row=r, column=idx).value or ""))
                                          for r in range(2, min(n + 2, 200))])
        ws.column_dimensions[get_column_letter(idx)].width = min(max(width + 3, 10), 45)
    ws.freeze_panes = "A2"
    return ws


def _to_bytes(wb: Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _subj(row: dict, lang: str) -> str:
    return (row.get("subject_names") or {}).get(lang) or row["subject"]


def _pct(v):
    return v if v is not None else ""


def groups_workbook(rows: list[dict], lang: str) -> bytes:
    t = labels(lang)
    wb = Workbook()
    headers = [t["group"], t["pupils"], t["attendance"], t["present"], t["late"], t["absent"],
               t["excused"], t["avg"], t["grades"], t["homeworks"], t["submission"], t["activity"]]
    data = [[r["group_name"], r["pupils"], _pct(r["attendance_rate"]), r["attendance"]["present"],
             r["attendance"]["late"], r["attendance"]["absent"], r["attendance"]["excused"],
             _pct(r["avg_grade"]), r["grades_count"], r["homeworks"], _pct(r["submission_rate"]),
             _pct(r["activity"])] for r in rows]
    _sheet(wb, t["groups_sheet"], headers, data, first=True)
    return _to_bytes(wb)


def teacher_workbook(stats: dict, att_rows: list[dict], grade_rows: list[dict], lang: str) -> bytes:
    t = labels(lang)
    wb = Workbook()
    headers = [t["student"], t["group"], t["attendance"], t["present"], t["late"], t["absent"],
               t["excused"], t["avg"], t["grades"], t["homeworks"], t["submitted"], t["hw_avg"]]
    data = [[p["student_name"], p["group_name"], _pct(p["attendance_rate"]), p["attendance"]["present"],
             p["attendance"]["late"], p["attendance"]["absent"], p["attendance"]["excused"],
             _pct(p["avg_grade"]), p["grades_count"], p["homeworks"], p["submitted"],
             _pct(p["homework_avg"])] for p in stats["pupils"]]
    _sheet(wb, t["pupils_sheet"], headers, data, first=True)
    _sheet(wb, t["att_sheet"], [t["date"], t["group"], t["subject"], t["student"], t["status"]],
           [[r["date"], r["group"], _subj(r, lang), r["student"], t.get(r["status"], r["status"])]
            for r in att_rows])
    _sheet(wb, t["grades_sheet"],
           [t["date"], t["group"], t["subject"], t["student"], t["score"], t["type"], t["comment"]],
           [[r["date"], r["group"], _subj(r, lang), r["student"], r["score"],
             t.get(r["type"], r["type"]), r["comment"]] for r in grade_rows])
    return _to_bytes(wb)


def pupil_workbook(pupil_name: str, stats: dict, grades: list[dict], attendance: list[dict],
                   homeworks: list[dict], lang: str) -> bytes:
    t = labels(lang)
    wb = Workbook()
    period = f"{stats['date_from']} — {stats['date_to']}" if stats["date_from"] else t["all"]
    a, g, h = stats["attendance"], stats["grades"], stats["homework"]
    summary = [
        [t["pupil"], pupil_name], [t["group"], stats["group_name"] or ""], [t["period"], period],
        [t["avg"], _pct(g["avg"])], [t["grades"], g["count"]],
        [t["attendance"], _pct(a["rate"])], [t["present"], a["present"]], [t["late"], a["late"]],
        [t["absent"], a["absent"]], [t["excused"], a["excused"]],
        [t["homeworks"], h["total"]], [t["submitted"], h["submitted"]],
        [t["submission"], _pct(h["rate"])], [t["hw_avg"], _pct(h["avg_score"])],
        [t["activity"], _pct(stats["activity"])],
    ]
    _sheet(wb, t["summary"], [t["metric"], t["value"]], summary, first=True)
    _sheet(wb, t["grades_sheet"], [t["date"], t["subject"], t["score"], t["type"], t["comment"]],
           [[r["date"], _subj(r, lang), r["score"], t.get(r["type"], r["type"]), r["comment"]]
            for r in grades])
    _sheet(wb, t["att_sheet"], [t["date"], t["subject"], t["status"]],
           [[r["date"], _subj(r, lang), t.get(r["status"], r["status"])] for r in attendance])
    _sheet(wb, t["hw_sheet"], [t["title"], t["subject"], t["deadline"], t["submitted"], t["score"]],
           [[r["title"], _subj(r, lang), r["deadline"], t["yes"] if r["submitted"] else t["no"],
             _pct(r["score"])] for r in homeworks])
    return _to_bytes(wb)
