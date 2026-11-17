import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (Group, GroupStudent, GroupSubject, Homework, HomeworkSubmission,
                        Material, RoleEnum, StoredFile, User)

ALLOWED_EXTENSIONS = {
    # hujjatlar
    "txt", "md", "csv", "pdf", "doc", "docx", "odt", "rtf",
    "ppt", "pptx", "odp", "xls", "xlsx", "ods",
    # arxivlar
    "zip", "rar", "7z", "tar", "gz",
    # rasm, audio, video
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "mp3", "wav", "mp4", "mov", "avi", "mkv",
    # dasturlash
    "py", "ipynb", "java", "c", "cpp", "cs", "sql", "json", "xml",
}


def upload_dir() -> Path:
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_path(stored: StoredFile) -> Path:
    return upload_dir() / stored.stored_name


def _safe_name(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]          # yo'l qismini olib tashlaymiz
    name = re.sub(r"[\x00-\x1f]", "", name).strip()
    return name[:200] or "file"


def save_upload(db: Session, user: User, upload: UploadFile) -> StoredFile:
    name = _safe_name(upload.filename or "file")
    ext = Path(name).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"'.{ext}' turidagi fayl yuklash mumkin emas")

    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest = upload_dir() / stored_name
    size = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Fayl hajmi {settings.MAX_UPLOAD_MB} MB dan oshmasligi kerak")
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Fayl bo'sh")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

    obj = StoredFile(original_name=name, stored_name=stored_name,
                     content_type=upload.content_type, size=size, uploader_id=user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def require_own_file(db: Session, user: User, file_id: Optional[int]) -> Optional[StoredFile]:
    """Biriktirilayotgan fayl shu foydalanuvchining o'zi yuklagan fayli bo'lishi shart."""
    if file_id is None:
        return None
    obj = db.get(StoredFile, file_id)
    if obj is None or obj.uploader_id != user.id:
        raise HTTPException(status_code=400, detail="Fayl topilmadi. Avval faylni qayta yuklang")
    return obj


def can_access(db: Session, user: User, f: StoredFile) -> bool:
    if user.role == RoleEnum.admin or f.uploader_id == user.id:
        return True

    group_id = None
    if user.role == RoleEnum.pupil:
        link = db.query(GroupStudent).filter(GroupStudent.student_id == user.id).first()
        group_id = link.group_id if link else None

    # Uy vazifasiga biriktirilgan fayl
    for hw in db.query(Homework).filter(Homework.file_id == f.id).all():
        if user.role == RoleEnum.teacher and hw.teacher_id == user.id:
            return True
        if user.role == RoleEnum.pupil and group_id == hw.group_id:
            return True

    # O'quvchining topshirgan ishi: o'qituvchi va o'quvchining o'zi ko'ra oladi
    for sub in db.query(HomeworkSubmission).filter(HomeworkSubmission.file_id == f.id).all():
        if user.role == RoleEnum.pupil and sub.student_id == user.id:
            return True
        if user.role == RoleEnum.teacher and sub.homework.teacher_id == user.id:
            return True

    # Material fayli
    for mat in db.query(Material).filter(Material.file_id == f.id).all():
        if user.role == RoleEnum.teacher and mat.teacher_id == user.id:
            return True
        if user.role == RoleEnum.pupil and group_id is not None:
            if db.query(GroupSubject).filter(GroupSubject.group_id == group_id,
                                             GroupSubject.subject_id == mat.subject_id).first():
                return True
    return False


def get_file_for_user(db: Session, user: User, file_id: int) -> StoredFile:
    obj = db.get(StoredFile, file_id)
    # Ruxsat yo'q bo'lsa ham 404: fayl mavjudligi oshkor bo'lmasin
    if obj is None or not can_access(db, user, obj):
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    if not file_path(obj).exists():
        raise HTTPException(status_code=404, detail="Fayl serverdan topilmadi")
    return obj


def _is_referenced(db: Session, file_id: int) -> bool:
    return bool(
        db.query(Homework.id).filter(Homework.file_id == file_id).first()
        or db.query(HomeworkSubmission.id).filter(HomeworkSubmission.file_id == file_id).first()
        or db.query(Material.id).filter(Material.file_id == file_id).first()
    )


def delete_if_orphan(db: Session, file_id: Optional[int]) -> None:
    """Hech qayerda ishlatilmayotgan faylni bazadan va diskdan o'chiradi."""
    if file_id is None:
        return
    obj = db.get(StoredFile, file_id)
    if obj is None or _is_referenced(db, file_id):
        return
    path = file_path(obj)
    db.delete(obj)
    db.commit()
    path.unlink(missing_ok=True)


def cleanup_unattached(db: Session, older_than_hours: int = 24) -> int:
    """Yuklangan, lekin hech narsaga biriktirilmagan eski fayllarni tozalaydi."""
    border = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    removed = 0
    for obj in db.query(StoredFile).all():
        created = obj.created_at
        if created is None:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < border and not _is_referenced(db, obj.id):
            path = file_path(obj)
            db.delete(obj)
            db.commit()
            path.unlink(missing_ok=True)
            removed += 1
    return removed
