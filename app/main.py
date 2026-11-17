from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (jadvallar ro'yxatga olinishi uchun)
from app.config import settings
from app.core.seed import seed_admin
from app.crud import file as crud_file
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, files, pupil, stats, teacher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Vaqtinchalik: Alembic sozlangach create_all olib tashlanadi
    Base.metadata.create_all(bind=engine)
    crud_file.upload_dir()  # uploads papkasi bo'lmasa yaratiladi
    with SessionLocal() as db:
        status = seed_admin(db)  # .env dagi admin bazada bo'lmasa yaratiladi
        removed = crud_file.cleanup_unattached(db)  # hech narsaga biriktirilmagan eski fayllar
        print(f"[startup] admin: {status}, tozalangan fayllar: {removed}")
    yield


app = FastAPI(title="EduJournal API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Total-Count"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(pupil.router)
app.include_router(files.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"message": "EduJournal API ishlamoqda!"}
