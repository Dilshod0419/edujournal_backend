from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.crud import user as crud_user
from app.database import get_db
from app.models import User
from app.schemas.user import Token, UserPreferencesUpdate, UserResponse

router = APIRouter(prefix="/auth", tags=["Avtorizatsiya (Login)"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud_user.get_user_by_username(db, form_data.username)

    # Foydalanuvchi bo'lmasa ham parol tekshiriladi (javob vaqti bir xil bo'lishi uchun)
    password_ok = verify_password(form_data.password, user.hashed_password if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profilingiz faolsizlantirilgan. Administratorga murojaat qiling",
        )

    # sub = user.id (login o'zgarsa ham token ma'nosini yo'qotmaydi), tv = token versiyasi
    token = create_access_token(subject=user.id, extra={"tv": user.token_version})
    return Token(access_token=token, role=user.role, full_name=user.full_name,
                 language=user.language, theme=user.theme)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/preferences", response_model=UserResponse)
def update_preferences(data: UserPreferencesUpdate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Til (uz/ru/en) va tema (light/dark) tanlovini saqlaydi."""
    return crud_user.update_preferences(db, current_user, data)
