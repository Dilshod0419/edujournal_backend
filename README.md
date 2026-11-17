# EduJournal backend (FastAPI + PostgreSQL)

    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env      # va ichini to'ldiring
    python reset_db.py          # jadvallarni yaratadi (barcha ma'lumot o'chadi!) va adminni qo'shadi
    uvicorn app.main:app --reload

Swagger: http://127.0.0.1:8000/docs

## Muhim qoidalar
- Baho va davomat bir marta saqlanadi: keyin o'zgartirib yoki o'chirib bo'lmaydi (409 xato).
- Parolni yangilash faqat parolni almashtiradi, login o'zgarmaydi.
- Fan va material nomi uch tilda (uz, ru, en) kiritiladi.
- `GET /admin/users/` sahifalab ishlaydi (`skip`, `limit`), jami soni `X-Total-Count` sarlavhasida.
