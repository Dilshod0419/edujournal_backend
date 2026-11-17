from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import file as crud_file
from app.database import get_db
from app.models import User
from app.schemas.file import FileInfo

router = APIRouter(prefix="/files", tags=["Fayllar"])


@router.post("/upload", response_model=FileInfo, status_code=201)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Fayl yuklash (maksimum MAX_UPLOAD_MB, odatda 20 MB). Qaytgan `id` ni vazifa,
    javob yoki materialga `file_id` sifatida biriktiring."""
    return crud_file.save_upload(db, user, file)


@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    obj = crud_file.get_file_for_user(db, user, file_id)
    return FileResponse(crud_file.file_path(obj), filename=obj.original_name,
                        media_type=obj.content_type or "application/octet-stream")
