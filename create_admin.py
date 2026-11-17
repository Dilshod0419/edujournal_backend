"""Admin yo'q bo'lsa yaratadi, bor bo'lsa parolini .env dagi ADMIN_PASSWORD ga qaytaradi."""
from app import models  # noqa: F401
from app.core.seed import seed_admin
from app.database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    print("Admin:", seed_admin(db, reset=True))
