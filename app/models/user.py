from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, func
from sqlalchemy.sql import expression

from app.database import Base
from app.models.enum import RoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(RoleEnum, name="roleenum"), nullable=False, index=True)

    is_active = Column(Boolean, nullable=False, default=True, server_default=expression.true())
    # Parol yangilanganda yoki profil faolsizlantirilganda oshiriladi: eski tokenlar bekor bo'ladi
    token_version = Column(Integer, nullable=False, default=0, server_default="0")

    language = Column(String(2), nullable=False, default="uz", server_default="uz")
    theme = Column(String(5), nullable=False, default="light", server_default="light")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
