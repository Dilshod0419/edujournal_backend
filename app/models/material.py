from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    material_type = Column(String(20), nullable=False, default="article")  # term | article | link | file
    title = Column(String(200), nullable=False)                 # o'zbekcha (asosiy)
    title_ru = Column(String(200), nullable=True)
    title_en = Column(String(200), nullable=True)
    content = Column(Text, nullable=False, default="")          # o'zbekcha matn yoki havola (URL)
    content_ru = Column(Text, nullable=True)
    content_en = Column(Text, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    subject = relationship("Subject", lazy="joined")
    file = relationship("StoredFile", lazy="joined")

    @property
    def subject_name(self) -> str:
        return self.subject.name

    @property
    def subject_names(self) -> dict:
        return self.subject.names
