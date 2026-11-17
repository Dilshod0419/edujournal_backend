"""DIQQAT: barcha jadvallar va ma'lumotlar o'chadi! Faqat rivojlanish bosqichida ishlating."""
from app import models  # noqa: F401
from app.core.seed import seed_admin
from app.database import Base, SessionLocal, engine

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Jadvallar qayta yaratildi")

with SessionLocal() as db:
    print("Admin:", seed_admin(db))
