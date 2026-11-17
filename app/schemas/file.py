import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FileInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size: int
    content_type: Optional[str] = None
    created_at: Optional[dt.datetime] = None
