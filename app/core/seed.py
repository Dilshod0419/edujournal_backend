from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import get_password_hash
from app.models import RoleEnum, User


def seed_admin(db: Session, reset: bool = False) -> str:
    """
    .env dagi ADMIN_USERNAME / ADMIN_PASSWORD bilan birinchi adminni yaratadi.
    Admin allaqachon bor bo'lsa tegmaydi. reset=True bo'lsa parolini .env dagiga qaytaradi.
    """
    username = settings.ADMIN_USERNAME.strip().lower()
    admin = db.query(User).filter(User.username == username).first()

    if admin is None:
        db.add(User(
            username=username,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            first_name="System",
            last_name="Admin",
            role=RoleEnum.admin,
        ))
        db.commit()
        return "created"

    if reset:
        admin.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
        admin.role = RoleEnum.admin
        admin.is_active = True
        admin.token_version += 1
        db.commit()
        return "reset"

    return "exists"
