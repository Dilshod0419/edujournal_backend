from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import file as crud_file
from app.crud.academic import get_group_subject_ids, get_pupil_group_id
from app.models import Material, TeacherSubject, User
from app.schemas.material import MaterialCreate, MaterialUpdate


def create_material(db: Session, teacher: User, data: MaterialCreate) -> Material:
    if not db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher.id,
                                           TeacherSubject.subject_id == data.subject_id).first():
        raise HTTPException(status_code=403, detail="Bu fan sizga biriktirilmagan")
    crud_file.require_own_file(db, teacher, data.file_id)
    obj = Material(**data.model_dump(), teacher_id=teacher.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_own_material(db: Session, teacher: User, material_id: int) -> Material:
    obj = db.get(Material, material_id)
    if obj is None or obj.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Material topilmadi")
    return obj


def list_teacher_materials(db: Session, teacher: User, subject_id: Optional[int] = None,
                           skip: int = 0, limit: int = 100):
    q = db.query(Material).filter(Material.teacher_id == teacher.id)
    if subject_id is not None:
        q = q.filter(Material.subject_id == subject_id)
    return q.order_by(Material.id.desc()).offset(skip).limit(limit).all()


def _filled(*values) -> bool:
    return all(v and v.strip() for v in values)


def _validate(db: Session, obj: Material) -> None:
    """Yangilashdan keyin materialning uch tildagi maydonlari to'liqligini tekshiradi."""
    problem = None
    if not _filled(obj.title, obj.title_ru, obj.title_en):
        problem = "Sarlavha uch tilda (uz, ru, en) kiritilishi kerak"
    elif obj.material_type == "file":
        if not obj.file_id:
            problem = "Fayl turidagi material uchun fayl kerak"
    elif obj.material_type == "link":
        if not (obj.content or "").strip():
            problem = "Matn yoki havola kiritilishi kerak"
    elif not _filled(obj.content, obj.content_ru, obj.content_en):
        problem = "Matn uch tilda (uz, ru, en) kiritilishi kerak"
    if problem:
        db.rollback()
        raise HTTPException(status_code=400, detail=problem)


def update_material(db: Session, teacher: User, material_id: int, data: MaterialUpdate) -> Material:
    obj = get_own_material(db, teacher, material_id)
    old_file_id = obj.file_id
    values = data.model_dump(exclude_unset=True)
    if "file_id" in values:
        crud_file.require_own_file(db, teacher, values["file_id"])
        obj.file_id = values.pop("file_id")
    for key, value in values.items():
        if value is not None:
            setattr(obj, key, value)
    _validate(db, obj)
    db.commit()
    if old_file_id != obj.file_id:
        crud_file.delete_if_orphan(db, old_file_id)
    db.refresh(obj)
    return obj


def delete_material(db: Session, teacher: User, material_id: int) -> None:
    obj = get_own_material(db, teacher, material_id)
    file_id = obj.file_id
    db.delete(obj)
    db.commit()
    crud_file.delete_if_orphan(db, file_id)


def list_pupil_materials(db: Session, pupil: User, subject_id: Optional[int] = None,
                         material_type: Optional[str] = None):
    """O'quvchi faqat o'z guruhiga biriktirilgan fanlar materiallarini ko'radi."""
    group_id = get_pupil_group_id(db, pupil.id)
    if group_id is None:
        return []
    allowed = get_group_subject_ids(db, group_id)
    if subject_id is not None:
        if subject_id not in allowed:
            raise HTTPException(status_code=403, detail="Bu fan sizning guruhingizga biriktirilmagan")
        allowed = [subject_id]
    q = db.query(Material).filter(Material.subject_id.in_(allowed))
    if material_type:
        q = q.filter(Material.material_type == material_type)
    return q.order_by(Material.id.desc()).all()
