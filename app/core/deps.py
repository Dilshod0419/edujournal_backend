from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.enum import RoleEnum
from app.models.user import User

# Swagger (/docs) dagi "Authorize" tugmasi shu manzil orqali token oladi
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token noto'g'ri yoki muddati tugagan",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profil faolsizlantirilgan",
        )

    # "Parolni yangilash" yoki faolsizlantirishdan keyin eski tokenlar yaroqsiz bo'ladi
    if payload.get("tv") != user.token_version:
        raise credentials_exception

    return user


def require_role(*roles: RoleEnum):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sizda bu amalni bajarish uchun ruxsat yo'q",
            )
        return current_user

    return checker


get_current_admin = require_role(RoleEnum.admin)
get_current_teacher = require_role(RoleEnum.teacher)
get_current_pupil = require_role(RoleEnum.pupil)
