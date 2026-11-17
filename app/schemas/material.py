import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.file import FileInfo

MaterialType = Literal["term", "article", "link", "file"]


def _filled(*values) -> bool:
    return all(v and v.strip() for v in values)


class MaterialCreate(BaseModel):
    """
    teacher_id yuborilmaydi: u tokendan olinadi.
    Sarlavha har uch tilda majburiy. Termin va maqola matni ham uch tilda majburiy.
    Havola (URL) tilga bog'liq emas, fayl turida matn ixtiyoriy.
    """
    subject_id: int
    material_type: MaterialType = "article"
    title: str = Field(min_length=1, max_length=200)
    title_ru: str = Field(min_length=1, max_length=200)
    title_en: str = Field(min_length=1, max_length=200)
    content: str = ""
    content_ru: Optional[str] = None
    content_en: Optional[str] = None
    file_id: Optional[int] = None

    @model_validator(mode="after")
    def check(self):
        if not _filled(self.title, self.title_ru, self.title_en):
            raise ValueError("Sarlavha uch tilda (uz, ru, en) kiritilishi kerak")
        if self.material_type == "file":
            if not self.file_id:
                raise ValueError("Fayl turidagi material uchun fayl yuklash kerak")
        elif self.material_type == "link":
            if not self.content.strip():
                raise ValueError("Matn yoki havola kiritilishi kerak")
        else:  # term | article
            if not _filled(self.content, self.content_ru, self.content_en):
                raise ValueError("Matn uch tilda (uz, ru, en) kiritilishi kerak")
        return self


class MaterialUpdate(BaseModel):
    material_type: Optional[MaterialType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    title_ru: Optional[str] = Field(default=None, min_length=1, max_length=200)
    title_en: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = None
    content_ru: Optional[str] = None
    content_en: Optional[str] = None
    file_id: Optional[int] = None  # null yuborilsa fayl olib tashlanadi


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    subject_name: str
    subject_names: dict[str, str]
    teacher_id: int
    material_type: str
    title: str
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    content: str
    content_ru: Optional[str] = None
    content_en: Optional[str] = None
    file: Optional[FileInfo] = None
    created_at: Optional[dt.datetime] = None
