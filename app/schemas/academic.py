from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_empty(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Nomi bo'sh bo'lmasligi kerak")
    return v


# --- Fan (uch tilda: o'zbekcha asosiy, ruscha va inglizcha majburiy) ---
class SubjectBase(BaseModel):
    name: str = Field(max_length=100)       # o'zbekcha
    name_ru: str = Field(max_length=100)
    name_en: str = Field(max_length=100)

    @field_validator("name", "name_ru", "name_en")
    @classmethod
    def not_empty(cls, v: str) -> str:
        return _not_empty(v)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(SubjectBase):
    pass


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    names: dict[str, str]


# --- Guruh (sinf) ---
class GroupBase(BaseModel):
    name: str = Field(max_length=50)

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        return _not_empty(v)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        return v if v is None else _not_empty(v)


class GroupResponse(GroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool = True


# --- Biriktirishlar ---
class SubjectRef(BaseModel):
    subject_id: int


class PupilRef(BaseModel):
    pupil_id: int


class TeacherAssign(BaseModel):
    teacher_id: int
    group_id: int
    subject_id: int


class GroupSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int
    subject_id: int
    group_name: str
    subject_name: str
    subject_names: dict[str, str]


class TeacherSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    subject_id: int
    subject_name: str
    subject_names: dict[str, str]


class TeacherAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    group_id: int
    subject_id: int
    teacher_name: str
    group_name: str
    subject_name: str
    subject_names: dict[str, str]
