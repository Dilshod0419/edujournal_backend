from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class StoredFile(Base):
    """Yuklangan fayl haqida ma'lumot. Faylning o'zi diskda (UPLOAD_DIR) turadi."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(100), unique=True, nullable=False)
    content_type = Column(String(150), nullable=True)
    size = Column(Integer, nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @property
    def name(self) -> str:
        return self.original_name
