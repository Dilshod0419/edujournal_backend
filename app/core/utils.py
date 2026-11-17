import re
import secrets
import string
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


# ---------- Login / parol ----------

def _clean(text: str) -> str:
    # O'ktam -> oktam, G'ayrat -> gayrat (apostrof va bo'shliqlar olib tashlanadi)
    return re.sub(r"[^a-z0-9]", "", text.strip().lower())


def generate_username(first_name: str, last_name: str) -> str:
    """Ali Valiyev -> ali_valiyev"""
    return f"{_clean(first_name)}_{_clean(last_name)}"


def generate_password() -> str:
    """8 belgi: 2 katta, 2 kichik, 2 raqam, 2 belgi (aralashtirilgan), faqat lotin."""
    chars = (
        [secrets.choice(string.ascii_uppercase) for _ in range(2)]
        + [secrets.choice(string.ascii_lowercase) for _ in range(2)]
        + [secrets.choice(string.digits) for _ in range(2)]
        + [secrets.choice("!@#$%^&*?") for _ in range(2)]
    )
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


# ---------- Vaqt (Toshkent vaqti) ----------

def get_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def now_local() -> datetime:
    return datetime.now(get_tz())


def today_local() -> date:
    return now_local().date()


def ensure_aware(dt: datetime) -> datetime:
    """Vaqt zonasiz kelgan sanani Toshkent vaqti deb hisoblaydi."""
    return dt if dt.tzinfo else dt.replace(tzinfo=get_tz())
