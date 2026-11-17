import datetime as dt
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enum import RoleEnum

_NAME_RE = re.compile(r"[A-Za-z]+(?:[ '\-ʻʼ’][A-Za-z]+)*")


def _check_name(v: str) -> str:
    v = v.strip()
    if not _NAME_RE.fullmatch(v):
        raise ValueError("Ism va familiya faqat lotin harflarida bo'lishi kerak")
    return v


class UserBase(BaseModel):
    first_name: str
    last_name: str
    role: RoleEnum

    @field_validator("first_name", "last_name")
    @classmethod
    def only_latin(cls, v: str) -> str:
        return _check_name(v)


class UserCreate(UserBase):
    """Admin faqat ism, familiya va rolni yuboradi. Login va parol avtomatik yasaladi."""
    group_id: Optional[int] = None  # o'quvchi yaratilganda darhol sinfga qo'shish uchun

    @field_validator("role")
    @classmethod
    def not_admin(cls, v: RoleEnum) -> RoleEnum:
        if v == RoleEnum.admin:
            raise ValueError("Admin faqat teacher yoki pupil yarata oladi")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def only_latin(cls, v: Optional[str]) -> Optional[str]:
        return v if v is None else _check_name(v)


class SubjectBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    names: dict[str, str] = {}


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str
    role: RoleEnum
    is_active: bool
    language: str = "uz"
    theme: str = "light"
    created_at: Optional[dt.datetime] = None

    # Faqat admin ro'yxatida to'ldiriladi: o'quvchining sinfi, o'qituvchining fanlari
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    subjects: Optional[list[SubjectBrief]] = None

    # Faqat yaratilganda yoki "Parolni yangilash" bosilganda, bir marta qaytadi
    generated_password: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None

    @field_validator("language")
    @classmethod
    def check_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"uz", "ru", "en"}:
            raise ValueError("Til uz, ru yoki en bo'lishi kerak")
        return v

    @field_validator("theme")
    @classmethod
    def check_theme(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"light", "dark"}:
            raise ValueError("Tema light yoki dark bo'lishi kerak")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    full_name: str
    language: str = "uz"
    theme: str = "light"
